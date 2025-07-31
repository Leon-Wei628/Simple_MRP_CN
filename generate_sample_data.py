import pandas as pd
import numpy as np
import os
import datetime
import random

# 确保示例数据目录存在
sample_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_data')
os.makedirs(sample_data_dir, exist_ok=True)

def generate_random_date(start_date, end_date):
    """
    生成指定范围内的随机日期
    """
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + datetime.timedelta(days=random_number_of_days)

def generate_large_sample_data(num_products=10, num_components=20, num_raw_materials=30, num_demand_records=50):
    """
    生成大规模示例数据
    
    参数:
    - num_products: 成品数量
    - num_components: 组件数量
    - num_raw_materials: 原材料数量
    - num_demand_records: 需求记录数量
    """
    # 生成物料编码
    product_codes = [f'P{i:03d}' for i in range(1, num_products + 1)]
    component_codes = [f'C{i:03d}' for i in range(1, num_components + 1)]
    raw_material_codes = [f'M{i:03d}' for i in range(1, num_raw_materials + 1)]
    
    all_materials = product_codes + component_codes + raw_material_codes
    
    # 生成物料名称
    material_names = {}
    for code in product_codes:
        material_names[code] = f'产品{code[1:]}'  # 例如: 产品001
    for code in component_codes:
        material_names[code] = f'组件{code[1:]}'  # 例如: 组件001
    for code in raw_material_codes:
        material_names[code] = f'原材料{code[1:]}'  # 例如: 原材料001
    
    # 生成BOM数据
    bom_data = []
    
    # 产品 -> 组件
    for product in product_codes:
        # 每个产品随机使用2-5个组件
        num_components_used = random.randint(2, min(5, len(component_codes)))
        selected_components = random.sample(component_codes, num_components_used)
        
        for component in selected_components:
            usage = random.randint(1, 5)  # 随机用量1-5
            bom_data.append({
                '父项编码': product,
                '父项名称': material_names[product],
                '子项编码': component,
                '子项名称': material_names[component],
                '用量': usage,
                '单位': '个'
            })
    
    # 组件 -> 原材料
    for component in component_codes:
        # 每个组件随机使用2-5个原材料
        num_materials_used = random.randint(2, min(5, len(raw_material_codes)))
        selected_materials = random.sample(raw_material_codes, num_materials_used)
        
        for material in selected_materials:
            usage = random.randint(1, 10)  # 随机用量1-10
            unit = random.choice(['个', 'kg', 'm', 'L'])  # 随机单位
            bom_data.append({
                '父项编码': component,
                '父项名称': material_names[component],
                '子项编码': material,
                '子项名称': material_names[material],
                '用量': usage,
                '单位': unit
            })
    
    # 生成库存数据
    inventory_data = []
    for material in all_materials:
        inventory = random.randint(10, 200)  # 随机库存10-200
        safety_stock = random.randint(5, 50)  # 随机安全库存5-50
        unit = random.choice(['个', 'kg', 'm', 'L']) if material in raw_material_codes else '个'  # 原材料随机单位，其他为个
        
        inventory_data.append({
            '物料编码': material,
            '物料名称': material_names[material],
            '库存数量': inventory,
            '安全库存': safety_stock,
            '单位': unit
        })
    
    # 生成生产计划
    production_plan = []
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=90)  # 未来90天内
    
    for _ in range(num_demand_records):
        product = random.choice(product_codes)  # 随机选择一个产品
        quantity = random.randint(50, 500)  # 随机需求量50-500
        date = generate_random_date(start_date, end_date)  # 随机日期
        
        production_plan.append({
            '产品编码': product,
            '产品名称': material_names[product],
            '需求数量': quantity,
            '需求日期': date.strftime('%Y-%m-%d')
        })
    
    # 按日期排序
    production_plan.sort(key=lambda x: x['需求日期'])
    
    # 生成采购订单
    purchase_orders = []
    po_start_date = start_date - datetime.timedelta(days=15)  # 从15天前开始
    po_end_date = start_date + datetime.timedelta(days=45)  # 到45天后结束
    
    for i, material in enumerate(raw_material_codes):
        # 每个原材料生成1-3个采购订单
        num_orders = random.randint(1, 3)
        
        for j in range(num_orders):
            order_date = generate_random_date(po_start_date, po_end_date - datetime.timedelta(days=15))
            delivery_date = order_date + datetime.timedelta(days=random.randint(7, 30))  # 交货期7-30天
            quantity = random.randint(30, 300)  # 随机订单量30-300
            unit = next((item['单位'] for item in inventory_data if item['物料编码'] == material), '个')
            supplier = f'供应商{random.choice("ABCDEFGHIJ")}'  # 随机供应商
            
            purchase_orders.append({
                '订单编号': f'PO{i+1:03d}-{j+1}',
                '物料编码': material,
                '物料名称': material_names[material],
                '订单数量': quantity,
                '单位': unit,
                '订单日期': order_date.strftime('%Y-%m-%d'),
                '预计到货日期': delivery_date.strftime('%Y-%m-%d'),
                '供应商': supplier
            })
    
    # 按到货日期排序
    purchase_orders.sort(key=lambda x: x['预计到货日期'])
    
    # 转换为DataFrame
    bom_df = pd.DataFrame(bom_data)
    inventory_df = pd.DataFrame(inventory_data)
    production_plan_df = pd.DataFrame(production_plan)
    purchase_orders_df = pd.DataFrame(purchase_orders)
    
    return bom_df, inventory_df, production_plan_df, purchase_orders_df

def save_sample_data(bom_df, inventory_df, production_plan_df, purchase_orders_df, prefix='large_'):
    """
    保存示例数据到CSV文件
    """
    bom_df.to_csv(os.path.join(sample_data_dir, f'{prefix}bom_data.csv'), index=False)
    inventory_df.to_csv(os.path.join(sample_data_dir, f'{prefix}inventory_data.csv'), index=False)
    production_plan_df.to_csv(os.path.join(sample_data_dir, f'{prefix}production_plan.csv'), index=False)
    purchase_orders_df.to_csv(os.path.join(sample_data_dir, f'{prefix}purchase_orders.csv'), index=False)
    
    print(f"已生成示例数据并保存到 {sample_data_dir} 目录")
    print(f"BOM数据: {len(bom_df)} 行")
    print(f"库存数据: {len(inventory_df)} 行")
    print(f"生产计划: {len(production_plan_df)} 行")
    print(f"采购订单: {len(purchase_orders_df)} 行")

if __name__ == "__main__":
    print("生成大规模示例数据...")
    bom_df, inventory_df, production_plan_df, purchase_orders_df = generate_large_sample_data(
        num_products=10,
        num_components=20,
        num_raw_materials=30,
        num_demand_records=50
    )
    
    save_sample_data(bom_df, inventory_df, production_plan_df, purchase_orders_df)
    
    print("\n生成中等规模示例数据...")
    bom_df, inventory_df, production_plan_df, purchase_orders_df = generate_large_sample_data(
        num_products=5,
        num_components=10,
        num_raw_materials=15,
        num_demand_records=25
    )
    
    save_sample_data(bom_df, inventory_df, production_plan_df, purchase_orders_df, prefix='medium_')
    
    print("\n示例数据生成完成!")