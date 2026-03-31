"""
数据库初始化脚本
创建所有表（pgvector 扩展可选）
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.core.database import engine, Base
from app.db.models import (
    User, MarketingData, KnowledgeDoc,
    DataTable, OperationLog
)


def create_extensions():
    """创建 PostgreSQL 扩展（可选）"""
    print("=" * 50)
    print("Step 1: 检查 PostgreSQL 扩展...")
    print("=" * 50)

    with engine.connect() as conn:
        try:
            # 尝试启用 pgvector 扩展（可选）
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("✅ pgvector 扩展已启用（支持向量相似度搜索）")
        except Exception as e:
            print(f"⚠️  pgvector 扩展未安装: {e}")
            print("💡 提示: 项目仍可正常运行，向量数据将存储为 Text")
            print("   如需向量相似度搜索性能优化，可后续安装 pgvector")
            # 不返回 False，继续执行
            print()

    return True


def drop_all_tables():
    """删除所有表（慎用！）"""
    print("\n" + "=" * 50)
    print("警告: 即将删除所有表！")
    print("=" * 50)

    confirm = input("确认删除所有表？(yes/no): ")
    if confirm.lower() != "yes":
        print("已取消")
        return

    Base.metadata.drop_all(engine)
    print("✅ 所有表已删除")


def create_all_tables():
    """创建所有表"""
    print("\n" + "=" * 50)
    print("Step 2: 创建数据库表...")
    print("=" * 50)

    try:
        Base.metadata.create_all(engine)
        print("\n✅ 数据库表创建成功！\n")

        # 显示创建的表
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print("已创建的表:")
        for table in tables:
            print(f"  - {table}")

        return True
    except Exception as e:
        print(f"\n❌ 创建表失败: {e}")
        return False


def create_admin_user():
    """创建默认管理员用户"""
    print("\n" + "=" * 50)
    print("Step 3: 创建默认管理员用户...")
    print("=" * 50)

    import hashlib
    from app.core.database import SessionLocal

    # 使用简单的 SHA-256 哈希（演示用，生产环境建议用 bcrypt）
    def hash_password(password: str) -> str:
        """简单的密码哈希函数"""
        return hashlib.sha256(password.encode()).hexdigest()

    db = SessionLocal()
    try:
        # 检查是否已存在管理员
        existing_admin = db.query(User).filter(User.employee_id == "admin001").first()
        if existing_admin:
            print("⚠️  管理员用户已存在，跳过创建")
            return

        # 创建管理员
        admin = User(
            employee_id="admin001",
            name="系统管理员",
            department="IT部门",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()

        print("\n✅ 默认管理员用户创建成功！")
        print("\n登录信息:")
        print("  工号: admin001")
        print("  密码: admin123")
        print("  角色: admin")
        print("\n⚠️  请在生产环境中修改默认密码！")

    except Exception as e:
        print(f"\n❌ 创建管理员失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("🚀 Z-Rop 数据库初始化")
    print("=" * 50 + "\n")

    # Step 1: 创建扩展
    if not create_extensions():
        print("\n❌ 扩展创建失败，退出初始化")
        return

    # Step 2: 创建表
    if not create_all_tables():
        print("\n❌ 表创建失败，退出初始化")
        return

    # Step 3: 创建管理员
    create_admin_user()

    print("\n" + "=" * 50)
    print("✅ 数据库初始化完成！")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库初始化脚本")
    parser.add_argument("--drop", action="store_true", help="删除所有表并重新创建")

    args = parser.parse_args()

    if args.drop:
        drop_all_tables()
        print()
        create_all_tables()
        create_admin_user()
    else:
        main()
