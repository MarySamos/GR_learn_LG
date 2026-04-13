# """
# 创建管理员用户脚本
# 用于添加新的管理员账号到数据库
# """
# import sys
# from pathlib import Path
#
# # 添加项目根目录到 Python 路径
# sys.path.insert(0, str(Path(__file__).parent.parent))
#
# import hashlib
# from app.core.database import SessionLocal
# from app.db.models import User
#
#
# def hash_password(password: str) -> str:
#     """密码哈希函数"""
#     return hashlib.sha256(password.encode()).hexdigest()
#
#
# def create_admin_user(employee_id: str, name: str, password: str, department: str = "IT部门"):
#     """
#     创建管理员用户
#
#     Args:
#         employee_id: 工号
#         name: 姓名
#         password: 密码
#         department: 部门
#     """
#     db = SessionLocal()
#     try:
#         # 检查用户是否已存在
#         existing_user = db.query(User).filter(User.employee_id == employee_id).first()
#         if existing_user:
#             print(f"⚠️  用户 {employee_id} 已存在")
#             print(f"   姓名: {existing_user.name}")
#             print(f"   角色: {existing_user.role}")
#             print(f"   状态: {'激活' if existing_user.is_active else '未激活'}")
#
#             # 询问是否更新密码
#             choice = input("\n是否要更新该用户的密码？(yes/no): ").lower()
#             if choice == "yes":
#                 existing_user.hashed_password = hash_password(password)
#                 existing_user.role = "admin"
#                 existing_user.is_active = True
#                 db.commit()
#                 print(f"\n✅ 用户 {employee_id} 的信息已更新")
#                 print(f"   新密码: {password}")
#                 print(f"   角色: admin")
#             return
#
#         # 创建新管理员
#     admin = User(
#         employee_id=employee_id,
#         name=name,
#         department=department,
#         hashed_password=hash_password(password),
#         role="admin",
#         is_active=True
#     )
#     db.add(admin)
#     db.commit()
#
#     print("\n" + "=" * 50)
#     print("✅ 管理员用户创建成功！")
#     print("=" * 50)
#     print(f"工号: {employee_id}")
#     print(f"姓名: {name}")
#     print(f"密码: {password}")
#     print(f"部门: {department}")
#     print(f"角色: admin")
#     print("=" * 50)
#
#     except Exception as e:
#         print(f"\n❌ 创建管理员失败: {e}")
#         import traceback
#         traceback.print_exc()
#         db.rollback()
#     finally:
#         db.close()
#
#
# def main():
#     """主函数"""
#     print("\n" + "=" * 50)
#     print("👤 创建管理员用户")
#     print("=" * 50 + "\n")
#
#     # 创建 samos 管理员账号
#     create_admin_user(
#         employee_id="samos",
#         name="Samos",
#         password="137900",
#         department="IT部门"
#     )
#
#     print("\n✅ 完成！您现在可以使用以下账号登录：")
#     print("  工号: samos")
#     print("  密码: 137900\n")
#
#
# if __name__ == "__main__":
#     main()
