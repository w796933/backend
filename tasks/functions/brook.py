from sqlalchemy.orm import Session

from app.db.models.port import Port

from app.db.models.port_forward import MethodEnum
from app.utils.dns import dns_query
from app.utils.ip import is_ip
from tasks.functions.base import AppConfig


class BrookConfig(AppConfig):
    method = MethodEnum.BROOK

    def __init__(self):
        super().__init__()
        self.app_name = "brook"


    def apply(self, db: Session, port: Port):
        self.local_port = port.num
        self.app_command = self.get_app_command(db, port)
        self.update_app = not port.server.config.get("brook")
        self.applied = True
        return self

    def get_app_command(self, db: Session, port: Port):
        command = port.forward_rule.config.get("command")
        if port.forward_rule.config.get("remote_address"):
            if not is_ip(port.forward_rule.config.get("remote_address")):
                remote_ip = dns_query(port.forward_rule.config.get("remote_address"))
            else:
                remote_ip = port.forward_rule.config.get("remote_address")
            port.forward_rule.config['remote_ip'] = remote_ip
            db.add(port.forward_rule)
            db.commit()
        if command == "relay":
            args = (
                f"-f :{port.num} "
                f"-t {remote_ip}:{port.forward_rule.config.get('remote_port')}"
            )
        elif command in ("server", "wsserver"):
            args = f"-l :{port.num} -p {port.forward_rule.config.get('password')}"
        elif command in ("client", "wsclient"):
            args = (
                f"--socks5 0.0.0.0:{port.num} "
                f"-s {remote_ip}:{port.forward_rule.config.get('remote_port')} "
                f"-p {port.forward_rule.config.get('password')}"
            )
        else:
            args = port.forward_rule.config.get("args")
        return f"/usr/local/bin/brook {command} {args}"

    @property
    def playbook(self):
        return "app.yml"
