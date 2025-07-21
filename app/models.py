from datetime import datetime

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func, Boolean
from sqlalchemy.dialects.postgresql import JSONB
try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    # 若未安装 pgvector，则使用 LargeBinary 作为占位符，防止导入错误
    from sqlalchemy import LargeBinary as Vector  # type: ignore
from sqlalchemy.orm import relationship


# 全局 Base，供各模型继承
Base = declarative_base()


class Company(Base):
    """潜力企业基础信息表"""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False, unique=True, index=True)
    domain = Column(String(256), nullable=True)
    province = Column(String(64), nullable=True)
    city = Column(String(64), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 关系映射
    entities = relationship(
        "DocEntity", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self):  # noqa: D401
        return f"<Company id={self.id} name={self.name!r}>"


class Document(Base):
    """采集到的原始文本统一入口"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(32))  # gov | wechat | media | social ...
    url = Column(String(512), unique=True)
    title = Column(String(256))
    content = Column(Text, nullable=False)
    publish_at = Column(DateTime(timezone=True))
    raw_json = Column(JSONB)
    embedding = Column(Vector(768), nullable=True)
    processed = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    company_hint = Column(String(256), nullable=True)

    def __repr__(self):  # noqa: D401
        return f"<Document id={self.id} source={self.source!r} url={self.url!r}>"


class DocEntity(Base):
    """文档级实体识别结果（行式存储）"""

    __tablename__ = "doc_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    ent_type = Column(String(32))  # PERSON / ORG / PRODUCT / TECH ...
    ent_text = Column(String(256))
    start = Column(Integer)
    end = Column(Integer)
    norm_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # 关系映射
    document = relationship("Document", backref="entities")
    company = relationship("Company", back_populates="entities")

    def __repr__(self):  # noqa: D401
        return f"<DocEntity id={self.id} type={self.ent_type} text={self.ent_text!r}>"


class JobPosting(Base):
    """51Job 招聘信息表"""

    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    salary = Column(String(64), nullable=True)
    location = Column(String(128), nullable=True)
    company_name = Column(String(256), nullable=True)
    post_date = Column(String(32), nullable=True)
    url = Column(String(512), unique=True, nullable=False)

    raw_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):  # noqa: D401
        return f"<JobPosting id={self.id} title={self.title!r} company={self.company_name!r}>"


# ------------------------------------------------------------
# 小红书笔记表
# ------------------------------------------------------------


class XHSNote(Base):
    """小红书笔记信息表"""

    __tablename__ = "xhs_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(256))
    desc = Column(Text)
    url = Column(String(512))
    user_id = Column(String(64))
    user_name = Column(String(128))
    like_count = Column(Integer)
    collect_count = Column(Integer)
    comment_count = Column(Integer)
    publish_time = Column(DateTime(timezone=True))

    raw_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):  # noqa: D401
        return f"<XHSNote id={self.id} note_id={self.note_id} title={self.title!r}>"
