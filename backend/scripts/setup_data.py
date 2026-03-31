"""
一键数据准备脚本

功能:
    1. 检查数据库连接
    2. 初始化数据库表结构
    3. 导入 CSV 营销数据
    4. (可选) 导入 PDF 知识文档
    5. (可选) 训练 ML 模型

使用方法:
    cd backend
    python scripts/setup_data.py

这是一个交互式脚本，会引导你完成所有数据准备工作。
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.database import Base


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_database_connection() -> bool:
    """检查数据库连接"""
    print_header("步骤 1: 检查数据库连接")

    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ 数据库连接成功!")
            print(f"   PostgreSQL 版本: {version[:50]}...")
            engine.dispose()
            return True
    except OperationalError as e:
        print(f"❌ 数据库连接失败!")
        print(f"   错误信息: {str(e)[:100]}...")
        print("\n💡 请确保:")
        print("   1. PostgreSQL 服务已启动")
        print("   2. .env 文件中的 DATABASE_URL 配置正确")
        print("   3. 数据库 'bank_agent' 已创建")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {str(e)}")
        return False


def init_database_tables() -> bool:
    """初始化数据库表结构"""
    print_header("步骤 2: 初始化数据库表结构")

    try:
        engine = create_engine(settings.DATABASE_URL)

        # 导入所有模型以确保它们被注册
        from app.db.models import User, MarketingData, KnowledgeDoc, DataTable, OperationLog

        # 创建所有表
        Base.metadata.create_all(bind=engine)

        # 检查表是否创建成功
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]

        print(f"✅ 数据库表初始化完成!")
        print(f"   已创建的表: {', '.join(tables)}")

        engine.dispose()
        return True

    except Exception as e:
        print(f"❌ 表创建失败: {str(e)}")
        return False


def check_csv_files() -> list:
    """检查可用的 CSV 数据文件"""
    data_dir = Path(__file__).parent.parent.parent / "data" / "raw"

    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)

    csv_files = list(data_dir.glob("*.csv"))
    return csv_files


def import_csv_data() -> bool:
    """导入 CSV 数据"""
    print_header("步骤 3: 导入营销数据")

    csv_files = check_csv_files()

    if not csv_files:
        print("⚠️  未找到 CSV 数据文件!")
        print(f"\n💡 请将 Kaggle 下载的数据放入:")
        print(f"   {Path(__file__).parent.parent.parent / 'data' / 'raw'}")
        print("\n   下载地址: https://www.kaggle.com/datasets/henriqueyamahata/bank-marketing")
        print("\n   支持的文件:")
        print("   - bank-additional-full.csv (推荐，41,188 条)")
        print("   - bank-additional.csv (10%样本，4,119 条)")
        print("   - bank-full.csv (旧版本，45,211 条)")
        return False

    print(f"📂 找到以下 CSV 文件:")
    for i, f in enumerate(csv_files, 1):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"   {i}. {f.name} ({size_mb:.2f} MB)")

    # 选择第一个文件进行导入
    selected_file = csv_files[0]
    print(f"\n📥 正在导入: {selected_file.name}")

    # 调用导入脚本
    from scripts.import_csv import load_and_validate_csv, preprocess_dataframe, import_to_database

    df = load_and_validate_csv(str(selected_file))
    if df is None:
        return False

    df_processed = preprocess_dataframe(df)
    success = import_to_database(df_processed, mode='replace')

    return success


def check_pdf_files() -> list:
    """检查可用的 PDF 知识文档"""
    docs_dir = Path(__file__).parent.parent.parent / "docs"

    if not docs_dir.exists():
        docs_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(docs_dir.glob("*.pdf"))
    return pdf_files


def import_pdf_documents() -> bool:
    """导入 PDF 知识文档（RAG 用）"""
    print_header("步骤 4: 导入知识文档 (PDF)")

    pdf_files = check_pdf_files()

    if not pdf_files:
        print("⚠️  未找到 PDF 知识文档")
        print(f"\n💡 如果需要 RAG 功能，请将 PDF 文档放入:")
        print(f"   {Path(__file__).parent.parent.parent / 'docs'}")
        print("\n   跳过此步骤...")
        return True  # 非必须步骤

    print(f"📄 找到以下 PDF 文件:")
    for f in pdf_files:
        size_kb = f.stat().st_size / 1024
        print(f"   - {f.name} ({size_kb:.1f} KB)")

    # 询问是否导入
    print("\n❓ 是否导入这些 PDF 文档? (需要 OpenAI API Key)")
    print("   输入 y 确认，其他键跳过: ", end="")

    try:
        user_input = input().strip().lower()
        if user_input != 'y':
            print("   跳过 PDF 导入...")
            return True
    except:
        print("   跳过 PDF 导入...")
        return True

    # TODO: 调用 ingest_pdf.py
    print("📥 正在导入 PDF 文档...")
    try:
        from scripts.ingest_pdf import PDFIngestor
        ingestor = PDFIngestor()
        docs_dir = str(Path(__file__).parent.parent.parent / "docs")
        ingestor.process_directory(docs_dir)
        print("✅ PDF 文档导入完成!")
        return True
    except Exception as e:
        print(f"⚠️  PDF 导入出错: {str(e)}")
        print("   可以稍后手动运行: python scripts/ingest_pdf.py")
        return True


def train_ml_model() -> bool:
    """训练机器学习模型"""
    print_header("步骤 5: 训练 ML 预测模型")

    print("❓ 是否现在训练 ML 模型? (需要先导入数据)")
    print("   输入 y 确认，其他键跳过: ", end="")

    try:
        user_input = input().strip().lower()
        if user_input != 'y':
            print("   跳过模型训练...")
            print("   可以稍后运行: python scripts/train_model.py")
            return True
    except:
        print("   跳过模型训练...")
        return True

    print("🤖 正在训练模型...")
    try:
        from scripts.train_model import ModelTrainer
        trainer = ModelTrainer()
        trainer.run()
        print("✅ 模型训练完成!")
        return True
    except Exception as e:
        print(f"⚠️  模型训练出错: {str(e)}")
        print("   可以稍后手动运行: python scripts/train_model.py")
        return True


def print_summary(results: dict):
    """打印总结"""
    print_header("数据准备完成!")

    print("\n📋 执行结果:")
    status_map = {True: "✅ 成功", False: "❌ 失败", None: "⏭️  跳过"}

    for step, success in results.items():
        status = status_map.get(success, "❓ 未知")
        print(f"   {step}: {status}")

    print("\n🚀 接下来你可以:")
    print("   1. 启动后端服务: python -m uvicorn main:app --reload")
    print("   2. 访问 API 文档: http://127.0.0.1:8000/docs")
    print("   3. 开始开发 LangGraph 智能体!")


def main():
    """主函数"""
    print("\n" + "🏦" * 20)
    print("\n     Z-Rop 数据准备向导")
    print("\n" + "🏦" * 20)

    results = {}

    # 步骤 1: 检查数据库连接
    results["数据库连接"] = check_database_connection()
    if not results["数据库连接"]:
        print("\n⚠️  请先修复数据库连接问题，然后重新运行此脚本。")
        return

    # 步骤 2: 初始化表结构
    results["表结构初始化"] = init_database_tables()
    if not results["表结构初始化"]:
        print("\n⚠️  表结构创建失败，请检查错误信息。")
        return

    # 步骤 3: 导入 CSV 数据
    results["CSV 数据导入"] = import_csv_data()

    # 步骤 4: 导入 PDF 文档（可选）
    results["PDF 文档导入"] = import_pdf_documents()

    # 步骤 5: 训练 ML 模型（可选）
    results["ML 模型训练"] = train_ml_model()

    # 打印总结
    print_summary(results)


if __name__ == "__main__":
    main()
