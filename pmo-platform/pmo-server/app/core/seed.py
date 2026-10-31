"""初始化种子数据：角色、项目类型、管理员账号、部门。"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.identity import Role, User, Dept, RoleBinding
from app.models.project import ProjectType, StageTemplate, GateTemplate, Project, Program
from app.models.task import Wbs, Task, Dependency
from app.models.platform import Dictionary
from app.models.collab import NotificationRule
from app.models.collab import Ticket, TodoItem


def ensure_seed():
    db: Session = SessionLocal()
    try:
        _seed_roles(db)
        _seed_project_types(db)
        _seed_depts(db)
        _seed_admin(db)
        _seed_dictionary(db)
        _seed_notification_rules(db)
        _seed_demo_data(db)
        db.commit()
    finally:
        db.close()


def _seed_roles(db: Session):
    roles = [
        ("pmo_admin", "PMO 管理员", "global"),
        ("pmo_secrecy", "密级管理员", "global"),
        ("pm", "项目经理", "project"),
        ("dept_head", "部门主管", "dept"),
        ("member", "项目成员", "project"),
        ("program_owner", "专项负责人", "project"),
        ("exec", "高管/经营层", "global"),
        ("finance", "财务接口人", "global"),
        ("qa", "质量体系", "global"),
    ]
    for code, name, scope in roles:
        if not db.query(Role).filter(Role.code == code).first():
            db.add(Role(code=code, name=name, scope=scope, builtin=True))
    db.flush()


def _seed_project_types(db: Session):
    types = [
        ("chip_design", "芯片设计", 1),
        ("pkg_design", "芯片封装设计", 2),
        ("test_eng", "芯片测试工程", 3),
        ("hw_board", "硬件板卡设计", 4),
        ("software", "软件设计", 5),
        ("system", "整机设计", 6),
        ("cluster", "集群调测", 7),
        ("npi", "NPI 导入", 8),
        ("delivery", "客户交付专项", 9),
        ("solution", "解决方案专项", 10),
    ]
    for code, name, order in types:
        if not db.query(ProjectType).filter(ProjectType.code == code).first():
            db.add(ProjectType(code=code, name=name, sort_order=order))
    db.flush()

    # 给芯片设计类型加阶段+门禁模板
    pt = db.query(ProjectType).filter(ProjectType.code == "chip_design").first()
    if pt and not db.query(StageTemplate).filter(StageTemplate.type_id == pt.id).first():
        stages = [
            ("requirements", "需求分析", 1, True, 30),
            ("architecture", "架构设计", 2, True, 45),
            ("rtl_design", "RTL 设计", 3, True, 90),
            ("verification", "功能验证", 4, True, 120),
            ("tapeout", "流片", 5, True, 30),
            ("post_silicon", "硅后调试", 6, False, 60),
        ]
        stage_objs = []
        for code, name, order, is_core, days in stages:
            st = StageTemplate(type_id=pt.id, code=code, name=name, order_no=order, is_core=is_core, typical_days=days)
            db.add(st)
            stage_objs.append(st)
        db.flush()
        gates = [
            ("G1_req_signoff", "需求签审", 1, stage_objs[0], True, False),
            ("G2_arch_review", "架构评审", 2, stage_objs[1], True, False),
            ("G3_tapeout", "流片 Gate", 3, stage_objs[4], True, True),
            ("G4_bringup", "硅后 Bring-up", 4, stage_objs[5], False, False),
        ]
        for code, name, order, st, is_core, is_high in gates:
            db.add(GateTemplate(
                type_id=pt.id, stage_template_id=st.id, code=code, name=name,
                order_no=order, is_core=is_core, is_high_risk=is_high,
                enforce_mode="commitment",
            ))


def _seed_depts(db: Session):
    if db.query(Dept).count() == 0:
        root = Dept(name="公司总部", source_id="root", path="/1/", order_no=0, status="active")
        db.add(root)
        db.flush()
        children = [
            ("芯片设计部", "dept_chip", "/1/2/"),
            ("验证部", "dept_verif", "/1/3/"),
            ("封装测试部", "dept_pkg", "/1/4/"),
            ("软件部", "dept_sw", "/1/5/"),
            ("PMO 办公室", "dept_pmo", "/1/6/"),
        ]
        for name, sid, path in children:
            db.add(Dept(name=name, source_id=sid, path=path, parent_id=root.id, order_no=1, status="active"))
        db.flush()


def _seed_admin(db: Session):
    admin = db.query(User).filter(User.employee_no == "admin").first()
    if not admin:
        pmo_dept = db.query(Dept).filter(Dept.source_id == "dept_pmo").first()
        admin = User(
            employee_no="admin",
            name="系统管理员",
            email="admin@pmo.local",
            dept_id=pmo_dept.id if pmo_dept else None,
            title="PMO 管理员",
            status="active",
            password_hash=hash_password("admin123"),
            src_ldap=False,
            src_wechat=False,
            is_external=False,
        )
        db.add(admin)
        db.flush()
        # 绑定 pmo_admin 角色
        role = db.query(Role).filter(Role.code == "pmo_admin").first()
        if role:
            db.add(RoleBinding(user_id=admin.id, role_id=role.id, granted_by=admin.id))
    db.flush()


def _seed_dictionary(db: Session):
    dicts = [
        ("holiday", "20260101", "元旦"),
        ("ticket_type", "resource", "资源申请"),
        ("ticket_type", "support", "技术支持"),
        ("ticket_type", "decision", "请决策"),
        ("milestone_kind", "tapeout", "流片"),
        ("milestone_kind", "mp", "量产"),
        ("milestone_kind", "delivery", "交付"),
    ]
    for cat, code, name in dicts:
        if not db.query(Dictionary).filter(Dictionary.category == cat, Dictionary.code == code).first():
            db.add(Dictionary(category=cat, code=code, name=name))
    db.flush()


def _seed_notification_rules(db: Session):
    rules = [
        ("task_overdue", ["inapp", "wecom"], "realtime"),
        ("ticket_overdue", ["inapp", "wecom", "email"], "realtime"),
        ("gate_blocked", ["inapp", "wecom"], "daily_digest"),
        ("weekly_due", ["inapp", "wecom"], "realtime"),
    ]
    for ev, ch, freq in rules:
        if not db.query(NotificationRule).filter(NotificationRule.event_type == ev).first():
            db.add(NotificationRule(event_type=ev, channels=ch, freq_limit=freq))
    db.flush()


def _seed_demo_data(db: Session):
    """创建一个演示项目，便于直接查看效果。"""
    if db.query(Project).count() > 0:
        return

    admin = db.query(User).filter(User.employee_no == "admin").first()
    chip_dept = db.query(Dept).filter(Dept.source_id == "dept_chip").first()
    pt = db.query(ProjectType).filter(ProjectType.code == "chip_design").first()

    # 演示 Program
    pgm = Program(
        code="PGM-X2", name="X2 芯片产品", owner_user_id=admin.id,
        secrecy_level="internal", status="active",
        description="X2 系列芯片研发项目集",
    )
    db.add(pgm)
    db.flush()

    # 演示项目
    from datetime import date
    proj = Project(
        code="PRJ-CHIP-202611-001",
        name="X2 芯片设计项目",
        program_id=pgm.id,
        type_id=pt.id,
        pm_user_id=admin.id,
        dept_id=chip_dept.id,
        status="active",
        secrecy_level="internal",
        progress_pct=35.0,
        health="yellow",
        plan_start=date(2026, 11, 1),
        plan_end=date(2027, 12, 31),
        data_pedigree="trial",
        created_by=admin.id,
    )
    db.add(proj)
    db.flush()

    # WBS
    wbs_root = Wbs(project_id=proj.id, code="1", name="X2 芯片设计", level=1, order_no=1)
    db.add(wbs_root)
    db.flush()
    wbs_list = [
        ("1.1", "需求与架构", 2),
        ("1.2", "前端设计", 2),
        ("1.3", "验证", 2),
        ("1.4", "流片与封测", 2),
    ]
    wbs_objs = [wbs_root]
    for code, name, lvl in wbs_list:
        w = Wbs(project_id=proj.id, parent_id=wbs_root.id, code=code, name=name, level=lvl, order_no=len(wbs_objs))
        db.add(w)
        wbs_objs.append(w)
    db.flush()

    # 任务
    tasks_data = [
        ("需求规格书编写", wbs_objs[1], date(2026, 11, 1), date(2026, 11, 30), "done", 100),
        ("架构设计评审", wbs_objs[1], date(2026, 12, 1), date(2026, 12, 31), "in_progress", 60),
        ("RTL 编码", wbs_objs[2], date(2027, 1, 1), date(2027, 3, 31), "not_started", 0),
        ("DFT 插入", wbs_objs[2], date(2027, 2, 1), date(2027, 3, 15), "not_started", 0),
        ("功能验证", wbs_objs[3], date(2027, 3, 1), date(2027, 6, 30), "not_started", 0),
        ("覆盖率收敛", wbs_objs[3], date(2027, 5, 1), date(2027, 7, 31), "not_started", 0),
        ("流片 Tapeout", wbs_objs[4], date(2027, 8, 1), date(2027, 8, 31), "not_started", 0),
        ("封测 Bring-up", wbs_objs[4], date(2027, 9, 1), date(2027, 11, 30), "not_started", 0),
    ]
    task_objs = []
    for i, (name, wbs, ps, pe, st, prog) in enumerate(tasks_data):
        t = Task(
            project_id=proj.id, wbs_id=wbs.id, name=name,
            owner_user_id=admin.id, plan_start=ps, plan_end=pe,
            status=st, progress_pct=prog, priority=3,
            is_milestone=(i == 6),  # Tapeout 是里程碑
            created_by=admin.id,
        )
        db.add(t)
        task_objs.append(t)
    db.flush()

    # 依赖：Tapeout 依赖验证完成
    if len(task_objs) >= 7:
        db.add(Dependency(predecessor_task_id=task_objs[5].id, successor_task_id=task_objs[6].id, dep_type="FS"))
        db.add(Dependency(predecessor_task_id=task_objs[3].id, successor_task_id=task_objs[4].id, dep_type="FS"))
