"""Add config column to PortForwardRule

Revision ID: b81e963bbc32
Revises: 07d160e702e0
Create Date: 2020-10-31 23:33:53.139772

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b81e963bbc32'
down_revision = '07d160e702e0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('port_forward_rule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('config', sa.JSON(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('port_forward_rule', schema=None) as batch_op:
        batch_op.drop_column('config')

    # ### end Alembic commands ###