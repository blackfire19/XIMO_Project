"""add evaluations table

Revision ID: j0k2l4m6n8o0
Revises: i9j1k3l5m7n9
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'j0k2l4m6n8o0'
down_revision = 'i9j1k3l5m7n9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'evaluations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('evaluator_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.CheckConstraint('score >= 1 AND score <= 10', name='ck_evaluation_score'),
    )
    op.create_index('ix_evaluations_subject_id', 'evaluations', ['subject_id'])
    op.create_index('ix_evaluations_target', 'evaluations', ['target_type', 'target_id'])


def downgrade():
    op.drop_index('ix_evaluations_target', 'evaluations')
    op.drop_index('ix_evaluations_subject_id', 'evaluations')
    op.drop_table('evaluations')
