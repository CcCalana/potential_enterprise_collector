#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本 - 创建智联招聘相关表
"""

from sqlalchemy import Column, DateTime, Integer, String, Text, func, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

# 创建Base
Base = declarative_base()

class ZhilianJob(Base):
    """智联招聘职位信息表"""
    __tablename__ = "zhilian_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)  # 职位ID
    job_title = Column(String(256), nullable=False)  # 职位名称
    company_name = Column(String(256), nullable=False)  # 公司名称
    company_size = Column(String(64))  # 公司规模
    company_type = Column(String(64))  # 公司类型
    salary = Column(String(64))  # 薪资范围
    work_city = Column(String(64))  # 工作城市
    work_experience = Column(String(64))  # 工作经验要求
    education = Column(String(64))  # 学历要求
    job_type = Column(String(32))  # 工作类型（全职/兼职等）
    job_description = Column(Text)  # 职位描述
    job_requirements = Column(Text)  # 职位要求
    welfare = Column(Text)  # 福利待遇
    publish_time = Column(DateTime(timezone=True))  # 发布时间
    update_time = Column(DateTime(timezone=True))  # 更新时间
    job_url = Column(String(512))  # 职位详情链接
    
    # 原始JSON数据
    raw_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):  # noqa: D401
        return f"<ZhilianJob id={self.id} job_id={self.job_id} title={self.job_title!r}>"


def init_zhilian_db():
    """初始化智联招聘数据库表"""
    settings = get_settings()
    
    # 创建数据库引擎
    engine = create_engine(
        settings.db_uri,
        echo=settings.echo_sql,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    
    # 创建表
    Base.metadata.create_all(bind=engine)
    print("智联招聘数据库表创建成功！")
    
    return engine


if __name__ == "__main__":
    init_zhilian_db() 