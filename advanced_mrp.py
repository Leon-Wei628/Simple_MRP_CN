import pandas as pd
import numpy as np
from ortools.linear_solver import pywraplp

def calculate_advanced_mrp(production_plan, bom_data, inventory_data, purchase_orders=None, 
                         lead_times=None, lot_sizes=None, capacity_constraints=None):
    """
    高级物料需求计划(MRP)计算函数
    
    参数:
    - production_plan: 生产计划DataFrame
    - bom_data: BOM数据DataFrame
    - inventory_data: 库存数据DataFrame
    - purchase_orders: 采购订单DataFrame (可选)
    - lead_times: 物料提前期DataFrame (可选)
    - lot_sizes: 批量大小约束DataFrame (可选)
    - capacity_constraints: 产能约束DataFrame (可选)
    
    返回:
    - mrp_results: MRP计算结果DataFrame
    """
    # 1. 数据预处理和验证
    # 确保所有必要的列都存在
    required_columns = {
        'production_plan': ['产品编码', '需求数量', '需求日期'],
        'bom_data': ['父项编码', '子项编码', '用量'],
        'inventory_data': ['物料编码', '库存数量', '安全库存']
    }
    
    for df_name, cols in required_columns.items():
        df = eval(df_name)
        missing_cols = [col for col in cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"{df_name}缺少必要的列: {', '.join(missing_cols)}")
    
    # 2. 处理提前期数据
    if lead_times is not None:
        # 确保提前期数据有必要的列
        if not all(col in lead_times.columns for col in ['物料编码', '生产提前期', '采购提前期']):
            raise ValueError("提前期数据缺少必要的列: 物料编码, 生产提前期, 采购提前期")
        
        # 创建提前期映射
        production_lead_time_map = dict(zip(lead_times['物料编码'], lead_times['生产提前期']))
        purchase_lead_time_map = dict(zip(lead_times['物料编码'], lead_times['采购提前期']))
    else:
        # 默认提前期为0
        production_lead_time_map = {}
        purchase_lead_time_map = {}
    
    # 3. 处理批量大小约束
    if lot_sizes is not None:
        # 确保批量大小数据有必要的列
        if not all(col in lot_sizes.columns for col in ['物料编码', '最小批量', '批量倍数']):
            raise ValueError("批量大小数据缺少必要的列: 物料编码, 最小批量, 批量倍数")
        
        # 创建批量大小映射
        min_lot_size_map = dict(zip(lot_sizes['物料编码'], lot_sizes['最小批量']))
        lot_multiple_map = dict(zip(lot_sizes['物料编码'], lot_sizes['批量倍数']))
    else:
        # 默认无批量约束
        min_lot_size_map = {}
        lot_multiple_map = {}
    
    # 4. 处理产能约束
    if capacity_constraints is not None:
        # 确保产能约束数据有必要的列
        if not all(col in capacity_constraints.columns for col in ['资源编码', '日期', '可用产能']):
            raise ValueError("产能约束数据缺少必要的列: 资源编码, 日期, 可用产能")
        
        # 创建产能约束映射
        capacity_map = {}
        for _, row in capacity_constraints.iterrows():
            resource = row['资源编码']
            date = row['日期']
            capacity = row['可用产能']
            
            if resource not in capacity_map:
                capacity_map[resource] = {}
            
            capacity_map[resource][date] = capacity
    else:
        # 默认无产能约束
        capacity_map = {}
    
    # 5. 构建物料清单树结构
    def build_bom_tree(parent_item, bom_data, level=0, path=None):
        if path is None:
            path = []
        
        # 检查循环引用
        if parent_item in path:
            raise ValueError(f"检测到BOM循环引用: {' -> '.join(path + [parent_item])}")
        
        # 获取所有子项
        children = bom_data[bom_data['父项编码'] == parent_item]
        
        result = {}
        for _, row in children.iterrows():
            child_item = row['子项编码']
            quantity = row['用量']
            
            # 递归获取子项的子项
            child_tree = build_bom_tree(child_item, bom_data, level+1, path + [parent_item])
            
            result[child_item] = {
                'quantity': quantity,
                'level': level + 1,
                'children': child_tree
            }
        
        return result
    
    # 6. 计算总需求量，考虑提前期
    def get_all_requirements(item, quantity, date, bom_tree_node, level=0):
        """ 递归计算一个物料及其所有子物料的总需求，并考虑提前期 """
        # 获取物料的生产提前期
        prod_lead_time = production_lead_time_map.get(item, 0)
        adjusted_date = pd.to_datetime(date) - pd.Timedelta(days=prod_lead_time)

        # 添加当前物料的需求
        requirements = [{'物料编码': item, '需求数量': quantity, '需求日期': adjusted_date, '需求级别': level}]
        
        # 递归地为所有子物料计算需求
        for child_item, child_info in bom_tree_node.items():
            child_quantity = quantity * child_info['quantity']
            child_level = level + 1
            
            # 递归调用，传入子物料的BOM节点
            child_requirements = get_all_requirements(
                child_item, 
                child_quantity, 
                adjusted_date, # 子项的需求日期基于父项调整后的日期
                child_info.get('children', {}), # 使用.get避免叶节点出错
                child_level
            )
            requirements.extend(child_requirements)
            
        return requirements

    # 7. 构建所有产品的BOM树
    all_products = production_plan['产品编码'].unique()
    bom_trees = {}
    for product in all_products:
        bom_trees[product] = build_bom_tree(product, bom_data)

    # 8. 计算总需求
    all_requirements = []
    for _, row in production_plan.iterrows():
        product = row['产品编码']
        quantity = row['需求数量']
        date = row['需求日期']
        
        # 获取该产品的BOM树
        product_bom_tree = bom_trees.get(product, {})
        
        # 计算产品及其所有子项的需求
        product_requirements = get_all_requirements(product, quantity, date, product_bom_tree)
        all_requirements.extend(product_requirements)
    
    # 转换为DataFrame
    gross_requirements_df = pd.DataFrame(all_requirements)
    
    # 9. 按物料和日期汇总总需求
    gross_requirements_summary = gross_requirements_df.groupby(['物料编码', '需求日期']).agg(
        {'需求数量': 'sum'}
    ).reset_index()
    
    # 10. 考虑库存和安全库存
    # 创建物料-库存映射
    inventory_map = dict(zip(inventory_data['物料编码'], inventory_data['库存数量']))
    safety_stock_map = dict(zip(inventory_data['物料编码'], inventory_data['安全库存']))
    
    # 添加采购订单数据
    if purchase_orders is not None and not purchase_orders.empty:
        # 确保采购订单有必要的列
        required_po_cols = ['物料编码', '订单数量', '预计到货日期']
        missing_po_cols = [col for col in required_po_cols if col not in purchase_orders.columns]
        if not missing_po_cols:
            # 按物料和日期汇总采购订单
            po_summary = purchase_orders.groupby(['物料编码', '预计到货日期']).agg(
                {'订单数量': 'sum'}
            ).reset_index()
        else:
            po_summary = pd.DataFrame(columns=['物料编码', '预计到货日期', '订单数量'])
    else:
        po_summary = pd.DataFrame(columns=['物料编码', '预计到货日期', '订单数量'])
    
    # 11. 使用OR-Tools优化MRP计算
    # 获取所有唯一的物料和日期
    all_items = gross_requirements_summary['物料编码'].unique()
    all_dates = sorted(gross_requirements_summary['需求日期'].unique())
    
    # 创建结果列表
    mrp_results = []
    
    # 为每个物料计算MRP
    for item in all_items:
        # 获取物料的总需求
        item_requirements = gross_requirements_summary[gross_requirements_summary['物料编码'] == item]
        
        # 获取物料的库存和安全库存
        current_inventory = inventory_map.get(item, 0)
        safety_stock = safety_stock_map.get(item, 0)
        
        # 获取物料的采购订单
        item_pos = po_summary[po_summary['物料编码'] == item] if not po_summary.empty else pd.DataFrame()
        
        # 获取物料的批量约束
        min_lot_size = min_lot_size_map.get(item, 0)
        lot_multiple = lot_multiple_map.get(item, 1)
        
        # 获取物料的采购提前期
        purchase_lead_time = purchase_lead_time_map.get(item, 0)
        
        # 创建优化求解器
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            raise ValueError("无法创建求解器")
        
        # 创建变量：每个时间段的净需求量
        net_requirements = {}
        for date in all_dates:
            # 考虑批量约束
            if min_lot_size > 0 or lot_multiple > 1:
                # 使用整数变量
                net_requirements[date] = solver.IntVar(0, solver.infinity(), f'net_req_{item}_{date}')
            else:
                # 使用连续变量
                net_requirements[date] = solver.NumVar(0, solver.infinity(), f'net_req_{item}_{date}')
        
        # 创建约束
        # 1. 库存约束
        inventory_level = current_inventory
        for i, date in enumerate(all_dates):
            demand_on_date = item_requirements[item_requirements['需求日期'] == date]['需求数量'].sum() if date in item_requirements['需求日期'].values else 0
            po_on_date = item_pos[item_pos['预计到货日期'] == date]['订单数量'].sum() if not item_pos.empty and date in item_pos['预计到货日期'].values else 0
            
            # 批量约束
            is_produced = solver.BoolVar(f'is_produced_{item}_{date}')
            solver.Add(net_requirements[date] <= is_produced * 999999) # 大M方法
            solver.Add(net_requirements[date] >= is_produced * min_lot_size_map.get(item, 0))
            if lot_multiple_map.get(item, 1) > 1:
                # 引入一个整数变量来处理批量倍数
                lot_multiplier = solver.IntVar(0, solver.infinity(), f'lot_multiplier_{item}_{date}')
                solver.Add(net_requirements[date] == lot_multiplier * lot_multiple_map.get(item, 1))

            # 库存水平更新
            inventory_level += po_on_date + net_requirements[date] - demand_on_date
            solver.Add(inventory_level >= safety_stock)

        # 2. 产能约束
        for resource, date_capacity in capacity_map.items():
            for date, capacity in date_capacity.items():
                if date in all_dates:
                    # 假设每个物料消耗1单位资源
                    solver.Add(net_requirements[date] <= capacity)
        
        # 3. 目标函数：最小化总净需求量和库存持有成本
        objective = solver.Objective()
        
        # 净需求成本权重
        for date in all_dates:
            objective.SetCoefficient(net_requirements[date], 1)
        
        objective.SetMinimization()
        
        # 求解
        status = solver.Solve()
        
        # 处理结果
        if status == pywraplp.Solver.OPTIMAL:
            # 重新计算每个时间段的投影库存和净需求
            projected_inventory = current_inventory
            for date in all_dates:
                # 当前日期的需求
                date_req = item_requirements[item_requirements['需求日期'] == date]['需求数量'].sum() if date in item_requirements['需求日期'].values else 0
                
                # 当前日期的采购到货
                date_po = item_pos[item_pos['预计到货日期'] == date]['订单数量'].sum() if not item_pos.empty and date in item_pos['预计到货日期'].values else 0
                
                # 计算净需求
                net_req = net_requirements[date].SolutionValue()
                
                # 考虑采购提前期计算下单日期
                order_date = pd.to_datetime(date) - pd.Timedelta(days=purchase_lead_time)
                
                # 只有当净需求大于0时才添加到结果中
                if net_req > 0:
                    mrp_results.append({
                        '物料编码': item,
                        '需求周期': date,
                        '下单日期': order_date,
                        '总需求量': date_req,
                        '期初库存': projected_inventory,
                        '安全库存': safety_stock,
                        '采购到货': date_po,
                        '净需求量': net_req,
                        '期末库存': projected_inventory + date_po + net_req - date_req,
                        '生产提前期': production_lead_time_map.get(item, 0),
                        '采购提前期': purchase_lead_time
                    })
                
                # 更新投影库存
                projected_inventory = projected_inventory + date_po + net_req - date_req
        else:
            raise ValueError(f"无法为物料 {item} 找到最优解")
    
    # 12. 转换结果为DataFrame并返回
    return pd.DataFrame(mrp_results)

# 批量约束处理函数
def apply_lot_sizing(quantity, min_lot_size, lot_multiple):
    """
    应用批量约束规则
    
    参数:
    - quantity: 原始需求数量
    - min_lot_size: 最小批量
    - lot_multiple: 批量倍数
    
    返回:
    - adjusted_quantity: 调整后的数量
    """
    if quantity <= 0:
        return 0
    
    # 应用最小批量约束
    adjusted_quantity = max(quantity, min_lot_size)
    
    # 应用批量倍数约束
    if lot_multiple > 1:
        # 向上取整到批量倍数的整数倍
        remainder = adjusted_quantity % lot_multiple
        if remainder > 0:
            adjusted_quantity = adjusted_quantity + (lot_multiple - remainder)
    
    return adjusted_quantity

# 产能约束检查函数
def check_capacity_constraints(mrp_results, capacity_constraints, resource_requirements):
    """
    检查MRP结果是否满足产能约束
    
    参数:
    - mrp_results: MRP计算结果DataFrame
    - capacity_constraints: 产能约束DataFrame
    - resource_requirements: 资源需求DataFrame，指定每种物料生产所需的资源和数量
    
    返回:
    - capacity_check_results: 产能检查结果DataFrame
    """
    # 确保输入数据有必要的列
    if not all(col in capacity_constraints.columns for col in ['资源编码', '日期', '可用产能']):
        raise ValueError("产能约束数据缺少必要的列: 资源编码, 日期, 可用产能")
    
    if not all(col in resource_requirements.columns for col in ['物料编码', '资源编码', '单位用量']):
        raise ValueError("资源需求数据缺少必要的列: 物料编码, 资源编码, 单位用量")
    
    # 创建资源需求映射
    resource_req_map = {}
    for _, row in resource_requirements.iterrows():
        item = row['物料编码']
        resource = row['资源编码']
        usage = row['单位用量']
        
        if item not in resource_req_map:
            resource_req_map[item] = {}
        
        resource_req_map[item][resource] = usage
    
    # 创建产能约束映射
    capacity_map = {}
    for _, row in capacity_constraints.iterrows():
        resource = row['资源编码']
        date = row['日期']
        capacity = row['可用产能']
        
        if resource not in capacity_map:
            capacity_map[resource] = {}
        
        capacity_map[resource][date] = capacity
    
    # 计算每个资源在每个日期的使用量
    resource_usage = {}
    for _, row in mrp_results.iterrows():
        item = row['物料编码']
        date = row['需求周期']
        quantity = row['净需求量']
        
        # 如果物料需要使用资源
        if item in resource_req_map:
            for resource, usage_per_unit in resource_req_map[item].items():
                # 计算总资源使用量
                total_usage = quantity * usage_per_unit
                
                if resource not in resource_usage:
                    resource_usage[resource] = {}
                
                if date not in resource_usage[resource]:
                    resource_usage[resource][date] = 0
                
                resource_usage[resource][date] += total_usage
    
    # 检查产能约束
    capacity_check_results = []
    for resource in resource_usage:
        for date in resource_usage[resource]:
            usage = resource_usage[resource][date]
            capacity = capacity_map.get(resource, {}).get(date, float('inf'))
            
            is_violated = usage > capacity
            
            capacity_check_results.append({
                '资源编码': resource,
                '日期': date,
                '资源使用量': usage,
                '可用产能': capacity,
                '是否超出产能': is_violated,
                '超出量': max(0, usage - capacity)
            })
    
    return pd.DataFrame(capacity_check_results)

# 物料分类函数
def classify_materials(bom_data, inventory_data):
    """
    对物料进行分类（原材料、中间件、成品）
    
    参数:
    - bom_data: BOM数据DataFrame
    - inventory_data: 库存数据DataFrame
    
    返回:
    - material_classification: 物料分类DataFrame
    """
    # 获取所有物料
    all_materials = set(inventory_data['物料编码'])
    
    # 获取所有父项和子项
    all_parents = set(bom_data['父项编码'])
    all_children = set(bom_data['子项编码'])
    
    # 分类物料
    raw_materials = all_materials & (all_children - all_parents)  # 只作为子项的物料
    finished_goods = all_materials & (all_parents - all_children)  # 只作为父项的物料
    intermediate_materials = all_materials & all_parents & all_children  # 既是父项又是子项的物料
    
    # 创建分类结果
    classification_results = []
    for material in all_materials:
        if material in raw_materials:
            material_type = '原材料'
        elif material in finished_goods:
            material_type = '成品'
        elif material in intermediate_materials:
            material_type = '中间件'
        else:
            material_type = '未知'
        
        classification_results.append({
            '物料编码': material,
            '物料类型': material_type
        })
    
    return pd.DataFrame(classification_results)