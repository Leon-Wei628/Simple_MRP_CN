import pandas as pd
import numpy as np
import io
import base64
import os
import datetime
import streamlit as st

def validate_production_plan(df):
    """
    验证生产计划数据格式
    
    参数:
    - df: 生产计划DataFrame
    
    返回:
    - is_valid: 是否有效
    - message: 错误信息（如果有）
    """
    required_columns = ['产品编码', '需求数量', '需求日期']
    
    # 检查必要的列
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"缺少必要的列: {', '.join(missing_columns)}"
    
    # 检查数据类型
    try:
        # 确保需求数量是数值型
        df['需求数量'] = pd.to_numeric(df['需求数量'])
        
        # 确保需求日期是日期型
        df['需求日期'] = pd.to_datetime(df['需求日期'])
    except Exception as e:
        return False, f"数据类型转换错误: {str(e)}"
    
    # 检查数据有效性
    if df['需求数量'].min() <= 0:
        return False, "需求数量必须大于0"
    
    return True, ""

def validate_bom_data(df):
    """
    验证BOM数据格式
    
    参数:
    - df: BOM数据DataFrame
    
    返回:
    - is_valid: 是否有效
    - message: 错误信息（如果有）
    """
    required_columns = ['父项编码', '子项编码', '用量']
    
    # 检查必要的列
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"缺少必要的列: {', '.join(missing_columns)}"
    
    # 检查数据类型
    try:
        # 确保用量是数值型
        df['用量'] = pd.to_numeric(df['用量'])
    except Exception as e:
        return False, f"数据类型转换错误: {str(e)}"
    
    # 检查数据有效性
    if df['用量'].min() <= 0:
        return False, "用量必须大于0"
    
    # 检查BOM循环引用
    try:
        check_bom_circular_reference(df)
    except ValueError as e:
        return False, str(e)
    
    return True, ""

def validate_inventory_data(df):
    """
    验证库存数据格式
    
    参数:
    - df: 库存数据DataFrame
    
    返回:
    - is_valid: 是否有效
    - message: 错误信息（如果有）
    """
    required_columns = ['物料编码', '库存数量', '安全库存']
    
    # 检查必要的列
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"缺少必要的列: {', '.join(missing_columns)}"
    
    # 检查数据类型
    try:
        # 确保库存数量和安全库存是数值型
        df['库存数量'] = pd.to_numeric(df['库存数量'])
        df['安全库存'] = pd.to_numeric(df['安全库存'])
    except Exception as e:
        return False, f"数据类型转换错误: {str(e)}"
    
    # 检查数据有效性
    if df['库存数量'].min() < 0:
        return False, "库存数量不能为负数"
    
    if df['安全库存'].min() < 0:
        return False, "安全库存不能为负数"
    
    return True, ""

def validate_purchase_orders(df):
    """
    验证采购订单数据格式
    
    参数:
    - df: 采购订单DataFrame
    
    返回:
    - is_valid: 是否有效
    - message: 错误信息（如果有）
    """
    required_columns = ['物料编码', '订单数量', '预计到货日期']
    
    # 检查必要的列
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"缺少必要的列: {', '.join(missing_columns)}"
    
    # 检查数据类型
    try:
        # 确保订单数量是数值型
        df['订单数量'] = pd.to_numeric(df['订单数量'])
        
        # 确保预计到货日期是日期型
        df['预计到货日期'] = pd.to_datetime(df['预计到货日期'])
    except Exception as e:
        return False, f"数据类型转换错误: {str(e)}"
    
    # 检查数据有效性
    if df['订单数量'].min() <= 0:
        return False, "订单数量必须大于0"
    
    return True, ""

def check_bom_circular_reference(bom_data):
    """
    检查BOM数据中是否存在循环引用
    
    参数:
    - bom_data: BOM数据DataFrame
    
    抛出:
    - ValueError: 如果检测到循环引用
    """
    # 创建物料依赖图
    dependency_graph = {}
    for _, row in bom_data.iterrows():
        parent = row['父项编码']
        child = row['子项编码']
        
        if parent not in dependency_graph:
            dependency_graph[parent] = []
        
        dependency_graph[parent].append(child)
    
    # 检查循环引用的辅助函数
    def check_cycle(item, path=None):
        if path is None:
            path = []
        
        # 检查是否已经在路径中
        if item in path:
            cycle_path = path[path.index(item):] + [item]
            raise ValueError(f"检测到BOM循环引用: {' -> '.join(cycle_path)}")
        
        # 如果物料有子项，递归检查
        if item in dependency_graph:
            for child in dependency_graph[item]:
                check_cycle(child, path + [item])
    
    # 检查每个物料
    for item in dependency_graph:
        check_cycle(item)

def get_download_link(df, filename, text):
    """
    生成DataFrame的下载链接
    
    参数:
    - df: 要下载的DataFrame
    - filename: 下载文件名
    - text: 链接显示文本
    
    返回:
    - href: HTML链接
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def load_sample_data(file_path):
    """
    加载示例数据
    
    参数:
    - file_path: 示例数据文件路径
    
    返回:
    - df: 加载的DataFrame
    """
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        st.error(f"加载示例数据时出错: {e}")
        return None

def generate_sample_data():
    """
    生成示例数据
    
    返回:
    - production_plan: 示例生产计划
    - bom_data: 示例BOM数据
    - inventory_data: 示例库存数据
    - purchase_orders: 示例采购订单
    """
    # 生成示例生产计划
    production_plan = pd.DataFrame({
        '产品编码': ['P001', 'P001', 'P002', 'P002'],
        '产品名称': ['产品A', '产品A', '产品B', '产品B'],
        '需求数量': [100, 150, 80, 120],
        '需求日期': ['2023-06-01', '2023-06-15', '2023-06-10', '2023-06-25']
    })
    
    # 生成示例BOM数据
    bom_data = pd.DataFrame({
        '父项编码': ['P001', 'P001', 'P002', 'P002', 'C001', 'C001', 'C002'],
        '父项名称': ['产品A', '产品A', '产品B', '产品B', '组件1', '组件1', '组件2'],
        '子项编码': ['C001', 'C002', 'C001', 'C003', 'M001', 'M002', 'M003'],
        '子项名称': ['组件1', '组件2', '组件1', '组件3', '原材料1', '原材料2', '原材料3'],
        '用量': [2, 3, 1, 2, 3, 2, 4],
        '单位': ['个', '个', '个', '个', 'kg', '个', '个']
    })
    
    # 生成示例库存数据
    inventory_data = pd.DataFrame({
        '物料编码': ['P001', 'P002', 'C001', 'C002', 'C003', 'M001', 'M002', 'M003'],
        '物料名称': ['产品A', '产品B', '组件1', '组件2', '组件3', '原材料1', '原材料2', '原材料3'],
        '库存数量': [20, 15, 50, 60, 40, 100, 150, 120],
        '安全库存': [10, 8, 20, 25, 15, 30, 40, 35],
        '单位': ['个', '个', '个', '个', '个', 'kg', '个', '个']
    })
    
    # 生成示例采购订单
    purchase_orders = pd.DataFrame({
        '订单编号': ['PO001', 'PO002', 'PO003', 'PO004', 'PO005'],
        '物料编码': ['M001', 'M002', 'M003', 'C001', 'C002'],
        '物料名称': ['原材料1', '原材料2', '原材料3', '组件1', '组件2'],
        '订单数量': [50, 80, 60, 20, 30],
        '单位': ['kg', '个', '个', '个', '个'],
        '订单日期': ['2023-05-15', '2023-05-16', '2023-05-18', '2023-05-15', '2023-05-20'],
        '预计到货日期': ['2023-05-30', '2023-06-02', '2023-06-05', '2023-06-05', '2023-06-10'],
        '供应商': ['供应商A', '供应商B', '供应商C', '供应商E', '供应商F']
    })
    
    return production_plan, bom_data, inventory_data, purchase_orders

def format_date_columns(df, date_columns):
    """
    格式化DataFrame中的日期列
    
    参数:
    - df: 要格式化的DataFrame
    - date_columns: 日期列名列表
    
    返回:
    - df: 格式化后的DataFrame
    """
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
    
    return df

def create_empty_dataframe(columns):
    """
    创建具有指定列的空DataFrame
    
    参数:
    - columns: 列名列表
    
    返回:
    - df: 空DataFrame
    """
    return pd.DataFrame(columns=columns)

def check_data_consistency(production_plan, bom_data, inventory_data):
    """
    检查数据一致性
    
    参数:
    - production_plan: 生产计划DataFrame
    - bom_data: BOM数据DataFrame
    - inventory_data: 库存数据DataFrame
    
    返回:
    - is_consistent: 是否一致
    - issues: 问题列表
    """
    issues = []
    
    # 获取所有物料编码
    production_items = set(production_plan['产品编码'])
    bom_parents = set(bom_data['父项编码'])
    bom_children = set(bom_data['子项编码'])
    inventory_items = set(inventory_data['物料编码'])
    
    all_items = production_items | bom_parents | bom_children
    
    # 检查生产计划中的产品是否在BOM中定义
    undefined_products = production_items - bom_parents
    if undefined_products:
        issues.append(f"生产计划中的以下产品在BOM中未定义为父项: {', '.join(undefined_products)}")
    
    # 检查所有物料是否都有库存记录
    missing_inventory = all_items - inventory_items
    if missing_inventory:
        issues.append(f"以下物料缺少库存记录: {', '.join(missing_inventory)}")
    
    return len(issues) == 0, issues

def analyze_bom_structure(bom_data):
    """
    分析BOM结构
    
    参数:
    - bom_data: BOM数据DataFrame
    
    返回:
    - analysis_results: 分析结果字典
    """
    # 获取所有父项和子项
    all_parents = set(bom_data['父项编码'])
    all_children = set(bom_data['子项编码'])
    
    # 计算各种物料类型
    raw_materials = all_children - all_parents  # 只作为子项的物料（原材料）
    finished_goods = all_parents - all_children  # 只作为父项的物料（成品）
    intermediate_materials = all_parents & all_children  # 既是父项又是子项的物料（中间件）
    
    # 计算BOM层级
    max_level = 0
    level_map = {}
    
    # 初始化成品为0级
    for item in finished_goods:
        level_map[item] = 0
    
    # 计算每个物料的层级
    def calculate_level(item, current_level=0):
        nonlocal max_level
        
        # 更新最大层级
        max_level = max(max_level, current_level)
        
        # 获取所有子项
        children = bom_data[bom_data['父项编码'] == item]['子项编码'].unique()
        
        for child in children:
            # 如果子项还没有层级或当前计算的层级更高，则更新
            if child not in level_map or level_map[child] < current_level + 1:
                level_map[child] = current_level + 1
                
                # 如果子项也是父项，递归计算
                if child in all_parents:
                    calculate_level(child, current_level + 1)
    
    # 从每个成品开始计算
    for item in finished_goods:
        calculate_level(item)
    
    # 统计每个层级的物料数量
    level_counts = {}
    for item, level in level_map.items():
        if level not in level_counts:
            level_counts[level] = 0
        level_counts[level] += 1
    
    # 返回分析结果
    return {
        'raw_materials_count': len(raw_materials),
        'finished_goods_count': len(finished_goods),
        'intermediate_materials_count': len(intermediate_materials),
        'total_items_count': len(all_parents | all_children),
        'max_bom_level': max_level,
        'level_distribution': level_counts
    }