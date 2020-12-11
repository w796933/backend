import re
import os
import hashlib
import typing as t
from datetime import datetime
from collections import defaultdict
from distutils.dir_util import copy_tree
from sqlalchemy.orm import joinedload, Session

from app.db.session import SessionLocal
from app.db.models.port import Port
from app.db.models.user import User
from app.db.models.server import Server
from app.db.models.port_forward import PortForwardRule
from app.db.crud.port import get_port_with_num
from app.db.crud.port_forward import delete_forward_rule, get_forward_rule
from app.db.crud.port_usage import create_port_usage, edit_port_usage
from app.db.crud.server import get_server, get_servers, get_server_users
from app.db.schemas.port_usage import PortUsageCreate, PortUsageEdit
from app.db.schemas.port_forward import PortForwardRuleOut
from app.db.schemas.server import ServerEdit
from tasks.utils.usage import update_traffic


def update_facts(server_id: int, facts: t.Dict, md5: str = None):
    db = SessionLocal()
    db_server = get_server(db, server_id)
    if facts.get("ansible_os_family"):
        db_server.config["system"] = {
            "os_family": facts.get("ansible_os_family"),
            "architecture": facts.get("ansible_architecture"),
            "distribution": facts.get("ansible_distribution"),
            "distribution_version": facts.get("ansible_distribution_version"),
            "distribution_release": facts.get("ansible_distribution_release"),
        }
    elif facts.get("msg"):
        db_server.config["system"] = {"msg": facts.get("msg")}
    # TODO: Add disable feature
    if "iptables" in facts:
        db_server.config["iptables"] = facts.get("iptables")
    if "gost" in facts:
        db_server.config["gost"] = facts.get("gost")
    if "v2ray" in facts:
        db_server.config["v2ray"] = facts.get("v2ray")
    if "brook" in facts:
        db_server.config["brook"] = facts.get("brook")
    if "socat" in facts:
        db_server.config["socat"] = facts.get("socat")
    if md5 is not None:
        db_server.config["init"] = md5
    db.add(db_server)
    db.commit()


def update_rule_error(server_id: int, port_id: int, error: str):
    db = SessionLocal()
    db_rule = get_forward_rule(db, server_id, port_id)
    db_rule.config["error"] = "\n".join(
        [
            re.search(r"\w+\[[0-9]+\]: (.*)$", line).group(1)
            for line in error.split("\n")
            if re.search(r"\w+\[[0-9]+\]: (.*)$", line)
        ]
    )
    db.add(db_rule)
    db.commit()


def iptables_finished_handler(server: Server, port_id: int = None, accumulate: bool = False):
    def wrapper(runner):
        facts = runner.get_fact_cache(server.ansible_name)
        if facts:
            if facts.get("traffic", ""):
                update_traffic(server, facts.get("traffic", ""), accumulate=accumulate)
            if port_id is not None and facts.get("error", ""):
                update_rule_error(server.id, port_id, facts.get("error"))
            update_facts(server.id, facts)
    return wrapper


def status_handler(port_id: int, status_data: dict, update_status: bool):
    if not update_status:
        return status_data

    db = SessionLocal()
    rule = (
        db.query(PortForwardRule)
        .filter(PortForwardRule.port_id == port_id)
        .first()
    )
    if rule:
        if (
            status_data.get("status", None) == "starting"
            and rule.status == "running"
        ):
            return status_data
        rule.status = status_data.get("status", None)
        db.add(rule)
        db.commit()
    return status_data