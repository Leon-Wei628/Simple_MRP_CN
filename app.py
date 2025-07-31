import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
import datetime
import os
from ortools.linear_solver import pywraplp

# 设置页面配置
st.set_page_config(page_title="物料需求计划(MRP)系统", page_icon="📊", layout="wide")

# 应用标题
st.title("物料需求计划(MRP)系统")
st.markdown("基于Streamlit和OR-Tools的物料需求计划计算工具")

# 初始化会话状态
if 'production_plan' not in st.session_state:
    st.session_state.production_plan = None
if 'bom_data' not in st.session_state:
    st.session_state.bom_data = None
if 'inventory_data' not in st.session_state:
    st.session_state.inventory_data = None
if 'purchase_orders' not in st.session_state:
    st.session_state.purchase_orders = None
if 'mrp_results' not in st.session_state:
    st.session_state.mrp_results = None

# 侧边栏 - 数据上传区域
with st.sidebar:
    st.header("数据上传")
    
    # 上传生产计划
    st.subheader("1. 上传生产计划")
    production_plan_file = st.file_uploader("选择生产计划CSV文件", type="csv", key="production_plan_uploader")
    if production_plan_file is not None:
        try:
            production_plan = pd.read_csv(production_plan_file)
            st.session_state.production_plan = production_plan
            st.success(f"成功加载生产计划: {production_plan.shape[0]}行 x {production_plan.shape[1]}列")
        except Exception as e:
            st.error(f"加载生产计划时出错: {e}")
    
    # 上传BOM数据
    st.subheader("2. 上传BOM数据")
    bom_file = st.file_uploader("选择BOM CSV文件", type="csv", key="bom_uploader")
    if bom_file is not None:
        try:
            bom_data = pd.read_csv(bom_file)
            st.session_state.bom_data = bom_data
            st.success(f"成功加载BOM数据: {bom_data.shape[0]}行 x {bom_data.shape[1]}列")
        except Exception as e:
            st.error(f"加载BOM数据时出错: {e}")
    
    # 上传库存数据
    st.subheader("3. 上传库存数据")
    inventory_file = st.file_uploader("选择库存CSV文件", type="csv", key="inventory_uploader")
    if inventory_file is not None:
        try:
            inventory_data = pd.read_csv(inventory_file)
            st.session_state.inventory_data = inventory_data
            st.success(f"成功加载库存数据: {inventory_data.shape[0]}行 x {inventory_data.shape[1]}列")
        except Exception as e:
            st.error(f"加载库存数据时出错: {e}")
    
    # 上传采购订单数据
    st.subheader("4. 上传采购订单数据")
    purchase_orders_file = st.file_uploader("选择采购订单CSV文件", type="csv", key="purchase_orders_uploader")
    if purchase_orders_file is not None:
        try:
            purchase_orders = pd.read_csv(purchase_orders_file)
            st.session_state.purchase_orders = purchase_orders
            st.success(f"成功加载采购订单数据: {purchase_orders.shape[0]}行 x {purchase_orders.shape[1]}列")
        except Exception as e:
            st.error(f"加载采购订单数据时出错: {e}")

    # MRP计算函数
    def calculate_mrp(production_plan, bom_data, inventory_data, purchase_orders=None):
        """
        计算物料需求计划(MRP)
        
        参数:
        - production_plan: 生产计划DataFrame，包含产品、数量和需求日期
        - bom_data: BOM数据DataFrame，包含父项、子项和用量
        - inventory_data: 库存数据DataFrame，包含物料和库存量
        - purchase_orders: 采购订单DataFrame，包含物料、数量和预计到货日期
        
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
        
        # 转换日期列为datetime对象
        production_plan['需求日期'] = pd.to_datetime(production_plan['需求日期'])
        if purchase_orders is not None and not purchase_orders.empty:
            purchase_orders['预计到货日期'] = pd.to_datetime(purchase_orders['预计到货日期'])
        
        # 2. 构建物料清单树结构
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
        
        # 3. 计算总需求量
        def get_all_requirements(item, quantity, date, bom_tree_node, level=0):
            """ 递归计算一个物料及其所有子物料的总需求 """
            # 添加当前物料的需求
            requirements = [{'物料编码': item, '需求数量': quantity, '需求日期': date, '需求级别': level}]
            
            # 递归地为所有子物料计算需求
            for child_item, child_info in bom_tree_node.items():
                child_quantity = quantity * child_info['quantity']
                child_level = level + 1
                
                # 假设子项需要提前一周准备 (可以后续配置为物料相关的提前期)
                child_date = pd.to_datetime(date) - pd.Timedelta(days=7)
                
                # 递归调用，传入子物料的BOM节点
                child_requirements = get_all_requirements(
                    child_item, 
                    child_quantity, 
                    child_date, 
                    child_info.get('children', {}), # 使用.get避免叶节点出错
                    child_level
                )
                requirements.extend(child_requirements)
                
            return requirements

        # 4. 构建所有产品的BOM树
        all_products = production_plan['产品编码'].unique()
        bom_trees = {}
        for product in all_products:
            bom_trees[product] = build_bom_tree(product, bom_data)

        # 5. 计算总需求
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
        
        # 6. 按物料和日期汇总总需求
        gross_requirements_summary = gross_requirements_df.groupby(['物料编码', '需求日期']).agg(
            {'需求数量': 'sum'}
        ).reset_index()
        
        # 7. 考虑库存和安全库存
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
        
        # 8. 使用OR-Tools优化MRP计算
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
            
            # 创建优化求解器
            solver = pywraplp.Solver.CreateSolver('SCIP')
            if not solver:
                raise ValueError("无法创建求解器")
            
            # 创建变量：每个时间段的净需求量
            net_requirements = {}
            for date in all_dates:
                net_requirements[date] = solver.NumVar(0, solver.infinity(), f'net_req_{item}_{date}')
            
            # 创建约束
            # 1. 库存约束：每个时间段的期末库存必须大于等于安全库存
            inventory_level = current_inventory
            for i, date in enumerate(all_dates):
                # 需求
                demand_on_date = item_requirements[item_requirements['需求日期'] == date]['需求数量'].sum() if date in item_requirements['需求日期'].values else 0
                # 采购到货
                po_on_date = item_pos[item_pos['预计到货日期'] == date]['订单数量'].sum() if not item_pos.empty and date in item_pos['预计到货日期'].values else 0
                
                # 定义期末库存的表达式
                # 期末库存 = 期初库存 + 采购到货 + 本期计划产出 - 本期需求
                inventory_level += po_on_date + net_requirements[date] - demand_on_date
                
                # 添加约束：期末库存 >= 安全库存
                solver.Add(inventory_level >= safety_stock)
            
            # 2. 目标函数：最小化总净需求量
            objective = solver.Objective()
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
                    
                    # 只有当净需求大于0时才添加到结果中
                    if net_req > 0:
                        mrp_results.append({
                            '物料编码': item,
                            '需求周期': date,
                            '总需求量': date_req,
                            '期初库存': projected_inventory,
                            '安全库存': safety_stock,
                            '采购到货': date_po,
                            '净需求量': net_req,
                            '期末库存': projected_inventory + date_po + net_req - date_req
                        })
                    
                    # 更新投影库存
                    projected_inventory = projected_inventory + date_po + net_req - date_req
            else:
                raise ValueError(f"无法为物料 {item} 找到最优解")
        
        # 9. 转换结果为DataFrame并返回
        return pd.DataFrame(mrp_results)

    # 计算按钮
    st.subheader("5. 运行MRP计算")
    if st.button("计算物料需求", key="calculate_mrp_button"):
        if (st.session_state.production_plan is not None and 
            st.session_state.bom_data is not None and 
            st.session_state.inventory_data is not None):
            with st.spinner("正在计算物料需求..."):
                try:
                    # 调用MRP计算函数
                    mrp_results = calculate_mrp(
                        st.session_state.production_plan,
                        st.session_state.bom_data,
                        st.session_state.inventory_data,
                        st.session_state.purchase_orders
                    )
                    st.session_state.mrp_results = mrp_results
                    st.success("MRP计算完成!")
                except Exception as e:
                    st.error(f"MRP计算过程中出错: {e}")
        else:
            st.warning("请先上传所有必要的数据文件(生产计划、BOM和库存)")

# 主界面 - 数据预览和结果展示
tab1, tab2, tab3, tab4, tab5 = st.tabs(["生产计划", "BOM数据", "库存数据", "采购订单", "MRP结果"])

# 生产计划预览
with tab1:
    st.header("生产计划数据预览")
    if st.session_state.production_plan is not None:
        st.dataframe(st.session_state.production_plan)
    else:
        st.info("请在侧边栏上传生产计划CSV文件")

# BOM数据预览
with tab2:
    st.header("BOM数据预览")
    if st.session_state.bom_data is not None:
        st.dataframe(st.session_state.bom_data)
    else:
        st.info("请在侧边栏上传BOM CSV文件")

# 库存数据预览
with tab3:
    st.header("库存数据预览")
    if st.session_state.inventory_data is not None:
        st.dataframe(st.session_state.inventory_data)
    else:
        st.info("请在侧边栏上传库存CSV文件")

# 采购订单预览
with tab4:
    st.header("采购订单数据预览")
    if st.session_state.purchase_orders is not None:
        st.dataframe(st.session_state.purchase_orders)
    else:
        st.info("请在侧边栏上传采购订单CSV文件(可选)")

# MRP结果展示
with tab5:
    st.header("物料需求计划(MRP)结果")
    if st.session_state.mrp_results is not None:
        # 显示MRP结果
        st.dataframe(st.session_state.mrp_results)
        
        # 提供下载结果的功能
        csv = st.session_state.mrp_results.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="mrp_results.csv">下载MRP结果CSV文件</a>'
        st.markdown(href, unsafe_allow_html=True)
        
        # 可视化MRP结果
        st.subheader("物料需求时间分布")
        try:
            # 假设MRP结果包含物料、周期和需求量
            pivot_table = st.session_state.mrp_results.pivot_table(
                index='物料编码', 
                columns='需求周期', 
                values='净需求量',
                aggfunc='sum',
                fill_value=0
            )
            st.bar_chart(pivot_table.T)  # 转置以便按时间显示
        except Exception as e:
            st.error(f"生成图表时出错: {e}")
    else:
        st.info("请先计算MRP结果")



# 运行应用
if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.info("""
    ### 关于本应用
    
    这是一个基于Streamlit和OR-Tools的物料需求计划(MRP)系统。
    
    上传您的生产计划、BOM、库存和采购订单数据，系统将计算物料需求并提供可视化结果。
    
    支持多层级BOM结构和优化计算。
    """)