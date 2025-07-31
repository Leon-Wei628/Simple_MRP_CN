@echo off
echo 正在启动物料需求计划(MRP)系统...

REM 检查Python是否已安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Python安装。请安装Python 3.7或更高版本。
    pause
    exit /b
)

REM 检查是否已安装依赖包
echo 检查依赖包...
pip show streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo 安装依赖包...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo 错误: 安装依赖包失败。
        pause
        exit /b
    )
)

REM 启动应用
echo 启动应用...
streamlit run app.py

pause