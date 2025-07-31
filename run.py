import streamlit as st
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入应用主模块
from app import *

# 如果直接运行此脚本
if __name__ == "__main__":
    # 显示欢迎信息
    print("启动物料需求计划(MRP)系统...")
    print("请在浏览器中访问: http://localhost:8501")
    
    # 启动Streamlit应用
    os.system("streamlit run app.py")