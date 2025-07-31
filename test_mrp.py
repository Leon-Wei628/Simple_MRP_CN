import pandas as pd
import numpy as np
import os
import sys
import time

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入MRP计算函数
from app import calculate_mrp
from advanced_mrp import calculate_advanced_mrp
from utils import validate_production_plan, validate_bom_data, validate_inventory_data, validate_purchase_orders

def load_test_data():
    """
    加载测试数据
    """
    sample_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_data')
    
    # 加载基本测试数据
    production_plan = pd.read_csv(os.path.join(sample_data_dir, 'production_plan.csv'))
    bom_data = pd.read_csv(os.path.join(sample_data_dir, 'bom_data.csv'))
    inventory_data = pd.read_csv(os.path.join(sample_data_dir, 'inventory_data.csv'))
    purchase_orders = pd.read_csv(os.path.join(sample_data_dir, 'purchase_orders.csv'))
    
    # 转换日期列
    production_plan['需求日期'] = pd.to_datetime(production_plan['需求日期'])
    purchase_orders['预计到货日期'] = pd.to_datetime(purchase_orders['预计到货日期'])
    
    return production_plan, bom_data, inventory_data, purchase_orders

def test_basic_mrp():
    """
    测试基本MRP计算功能
    """
    print("测试基本MRP计算功能...")
    
    # 加载测试数据
    production_plan, bom_data, inventory_data, purchase_orders = load_test_data()
    
    # 验证数据
    is_valid, message = validate_production_plan(production_plan)
    if not is_valid:
        print(f"生产计划数据验证失败: {message}")
        return False
    
    is_valid, message = validate_bom_data(bom_data)
    if not is_valid:
        print(f"BOM数据验证失败: {message}")
        return False
    
    is_valid, message = validate_inventory_data(inventory_data)
    if not is_valid:
        print(f"库存数据验证失败: {message}")
        return False
    
    is_valid, message = validate_purchase_orders(purchase_orders)
    if not is_valid:
        print(f"采购订单数据验证失败: {message}")
        return False
    
    # 计时开始
    start_time = time.time()
    
    try:
        # 计算MRP
        mrp_results = calculate_mrp(
            production_plan,
            bom_data,
            inventory_data,
            purchase_orders
        )
        
        # 计时结束
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 输出结果统计
        print(f"MRP计算成功完成，耗时: {elapsed_time:.2f}秒")
        print(f"结果包含 {len(mrp_results)} 行数据")
        print(f"涉及 {mrp_results['物料编码'].nunique()} 个物料")
        print(f"涉及 {mrp_results['需求周期'].nunique()} 个时间周期")
        
        # 输出部分结果示例
        print("\n结果示例:")
        print(mrp_results.head())
        
        return True
    except Exception as e:
        print(f"MRP计算失败: {e}")
        return False

def test_advanced_mrp():
    """
    测试高级MRP计算功能
    """
    print("\n测试高级MRP计算功能...")
    
    # 加载测试数据
    production_plan, bom_data, inventory_data, purchase_orders = load_test_data()
    
    # 创建提前期数据
    lead_times = pd.DataFrame({
        '物料编码': inventory_data['物料编码'],
        '生产提前期': np.random.randint(1, 7, size=len(inventory_data)),  # 1-7天的生产提前期
        '采购提前期': np.random.randint(3, 14, size=len(inventory_data))  # 3-14天的采购提前期
    })
    
    # 创建批量大小约束
    lot_sizes = pd.DataFrame({
        '物料编码': inventory_data['物料编码'],
        '最小批量': np.random.randint(10, 50, size=len(inventory_data)),  # 10-50的最小批量
        '批量倍数': np.random.choice([1, 5, 10, 20], size=len(inventory_data))  # 批量倍数
    })
    
    # 计时开始
    start_time = time.time()
    
    try:
        # 计算高级MRP
        mrp_results = calculate_advanced_mrp(
            production_plan,
            bom_data,
            inventory_data,
            purchase_orders,
            lead_times,
            lot_sizes
        )
        
        # 计时结束
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 输出结果统计
        print(f"高级MRP计算成功完成，耗时: {elapsed_time:.2f}秒")
        print(f"结果包含 {len(mrp_results)} 行数据")
        print(f"涉及 {mrp_results['物料编码'].nunique()} 个物料")
        print(f"涉及 {mrp_results['需求周期'].nunique()} 个时间周期")
        
        # 输出部分结果示例
        print("\n结果示例:")
        print(mrp_results.head())
        
        return True
    except Exception as e:
        print(f"高级MRP计算失败: {e}")
        return False

def test_performance_with_large_data():
    """
    使用大规模数据测试性能
    """
    print("\n使用大规模数据测试性能...")
    
    sample_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_data')
    large_data_files = [
        os.path.join(sample_data_dir, 'large_production_plan.csv'),
        os.path.join(sample_data_dir, 'large_bom_data.csv'),
        os.path.join(sample_data_dir, 'large_inventory_data.csv'),
        os.path.join(sample_data_dir, 'large_purchase_orders.csv')
    ]
    
    # 检查大规模数据文件是否存在
    if not all(os.path.exists(file) for file in large_data_files):
        print("大规模测试数据文件不存在，请先运行 generate_sample_data.py 生成测试数据")
        return False
    
    # 加载大规模测试数据
    production_plan = pd.read_csv(large_data_files[0])
    bom_data = pd.read_csv(large_data_files[1])
    inventory_data = pd.read_csv(large_data_files[2])
    purchase_orders = pd.read_csv(large_data_files[3])
    
    # 转换日期列
    production_plan['需求日期'] = pd.to_datetime(production_plan['需求日期'])
    purchase_orders['预计到货日期'] = pd.to_datetime(purchase_orders['预计到货日期'])
    
    # 输出数据规模
    print(f"生产计划: {len(production_plan)} 行, {production_plan['产品编码'].nunique()} 个产品")
    print(f"BOM数据: {len(bom_data)} 行, {bom_data['父项编码'].nunique()} 个父项, {bom_data['子项编码'].nunique()} 个子项")
    print(f"库存数据: {len(inventory_data)} 行")
    print(f"采购订单: {len(purchase_orders)} 行")
    
    # 计时开始
    start_time = time.time()
    
    try:
        # 计算MRP
        mrp_results = calculate_mrp(
            production_plan,
            bom_data,
            inventory_data,
            purchase_orders
        )
        
        # 计时结束
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 输出结果统计
        print(f"大规模MRP计算成功完成，耗时: {elapsed_time:.2f}秒")
        print(f"结果包含 {len(mrp_results)} 行数据")
        print(f"涉及 {mrp_results['物料编码'].nunique()} 个物料")
        print(f"涉及 {mrp_results['需求周期'].nunique()} 个时间周期")
        
        return True
    except Exception as e:
        print(f"大规模MRP计算失败: {e}")
        return False

if __name__ == "__main__":
    print("开始MRP系统测试...\n")
    
    # 测试基本MRP计算
    basic_test_result = test_basic_mrp()
    
    # 测试高级MRP计算
    advanced_test_result = test_advanced_mrp()
    
    # 检查大规模数据文件是否存在
    sample_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_data')
    large_data_exists = os.path.exists(os.path.join(sample_data_dir, 'large_bom_data.csv'))
    
    # 如果大规模数据存在，测试性能
    performance_test_result = False
    if large_data_exists:
        performance_test_result = test_performance_with_large_data()
    else:
        print("\n跳过大规模数据性能测试，因为大规模测试数据文件不存在")
        print("运行 generate_sample_data.py 可以生成大规模测试数据")
    
    # 输出总结果
    print("\n测试结果总结:")
    print(f"基本MRP计算测试: {'通过' if basic_test_result else '失败'}")
    print(f"高级MRP计算测试: {'通过' if advanced_test_result else '失败'}")
    if large_data_exists:
        print(f"大规模数据性能测试: {'通过' if performance_test_result else '失败'}")
    
    if basic_test_result and advanced_test_result and (not large_data_exists or performance_test_result):
        print("\n所有测试通过!")
        sys.exit(0)
    else:
        print("\n部分测试失败，请检查错误信息")
        sys.exit(1)