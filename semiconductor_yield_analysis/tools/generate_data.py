"""
半导体良率分析 - 数据生成模块
生成模拟的WAT、Defect、SPC、告警数据及对应的Wafer Map
场景: 某批次晶圆出现良率异常，需要通过多维度数据分析定位根因
根因设定: 光刻机边缘曝光不均匀，导致晶圆边缘区域缺陷增多
"""

import numpy as np
import pandas as pd
import os

WAFER_DIAMETER = 300  # mm
DIE_SIZE = 10  # mm
NUM_WAFERS = 25  # 一个lot 25片wafer
SEED = 42

np.random.seed(SEED)


def generate_die_coordinates():
    """生成晶圆上所有die的坐标 (基于300mm wafer)"""
    radius = WAFER_DIAMETER / 2
    dies = []
    n = int(radius / DIE_SIZE)
    for x in range(-n, n + 1):
        for y in range(-n, n + 1):
            cx = x * DIE_SIZE
            cy = y * DIE_SIZE
            # 检查die四个角是否都在晶圆内
            corners_inside = all(
                (cx + dx) ** 2 + (cy + dy) ** 2 <= (radius - 5) ** 2
                for dx in [-DIE_SIZE / 2, DIE_SIZE / 2]
                for dy in [-DIE_SIZE / 2, DIE_SIZE / 2]
            )
            if corners_inside:
                dies.append((x, y, cx, cy))
    return dies


def distance_from_center(cx, cy):
    return np.sqrt(cx ** 2 + cy ** 2)


def generate_yield_map(dies, wafer_id):
    """
    生成良率map - 根因: 边缘效应
    边缘区域die失效概率更高
    """
    records = []
    for die_x, die_y, cx, cy in dies:
        dist = distance_from_center(cx, cy)
        radius = WAFER_DIAMETER / 2

        # 基础良率 95%
        base_yield = 0.95

        # 边缘效应: 距离中心越远，失效概率越高
        edge_ratio = dist / radius
        if edge_ratio > 0.7:
            fail_prob = 0.15 + 0.5 * ((edge_ratio - 0.7) / 0.3) ** 2
        else:
            fail_prob = 0.05

        # 添加一些随机波动
        fail_prob += np.random.normal(0, 0.02)
        fail_prob = np.clip(fail_prob, 0, 1)

        # 某些wafer的边缘效应更严重 (模拟批次内差异)
        if wafer_id in [3, 7, 12, 18, 22]:
            if edge_ratio > 0.65:
                fail_prob *= 1.4

        pass_fail = 1 if np.random.random() > fail_prob else 0
        records.append({
            'wafer_id': wafer_id,
            'die_x': die_x,
            'die_y': die_y,
            'center_x_mm': cx,
            'center_y_mm': cy,
            'dist_from_center': round(dist, 2),
            'bin': pass_fail  # 1=pass, 0=fail
        })
    return records


def generate_wat_data(dies, wafer_id):
    """
    生成WAT (Wafer Acceptance Test) 数据
    测量参数: Vth(阈值电压), Idsat(饱和漏极电流), Rs(薄层电阻)
    边缘区域参数漂移更大
    """
    records = []
    for die_x, die_y, cx, cy in dies:
        dist = distance_from_center(cx, cy)
        radius = WAFER_DIAMETER / 2
        edge_ratio = dist / radius

        # Vth: 目标值0.45V, 边缘偏高
        vth_base = 0.45
        vth_shift = 0.08 * max(0, (edge_ratio - 0.6)) ** 1.5
        vth = vth_base + vth_shift + np.random.normal(0, 0.008)

        # Idsat: 目标值800uA, 边缘偏低
        idsat_base = 800
        idsat_shift = -120 * max(0, (edge_ratio - 0.6)) ** 1.5
        idsat = idsat_base + idsat_shift + np.random.normal(0, 15)

        # Rs: 目标值150 ohm/sq, 边缘偏高
        rs_base = 150
        rs_shift = 30 * max(0, (edge_ratio - 0.55)) ** 1.8
        rs = rs_base + rs_shift + np.random.normal(0, 3)

        records.append({
            'wafer_id': wafer_id,
            'die_x': die_x,
            'die_y': die_y,
            'center_x_mm': cx,
            'center_y_mm': cy,
            'dist_from_center': round(dist, 2),
            'Vth_V': round(vth, 4),
            'Idsat_uA': round(idsat, 2),
            'Rs_ohm_sq': round(rs, 2)
        })
    return records


def generate_defect_data(dies, wafer_id):
    """
    生成缺陷检测数据
    缺陷类型: particle(颗粒), scratch(划伤), pattern_defect(图形缺陷)
    边缘区域pattern_defect显著增多 (与光刻边缘曝光有关)
    """
    records = []
    for die_x, die_y, cx, cy in dies:
        dist = distance_from_center(cx, cy)
        radius = WAFER_DIAMETER / 2
        edge_ratio = dist / radius

        # 颗粒缺陷: 随机分布
        particle_count = np.random.poisson(0.3)

        # 划伤缺陷: 很少
        scratch_count = np.random.poisson(0.05)

        # 图形缺陷: 边缘区域显著增多 (根因)
        if edge_ratio > 0.7:
            pattern_lambda = 0.5 + 3.0 * ((edge_ratio - 0.7) / 0.3) ** 2
        else:
            pattern_lambda = 0.1
        pattern_defect_count = np.random.poisson(pattern_lambda)

        total_defects = particle_count + scratch_count + pattern_defect_count

        records.append({
            'wafer_id': wafer_id,
            'die_x': die_x,
            'die_y': die_y,
            'center_x_mm': cx,
            'center_y_mm': cy,
            'dist_from_center': round(dist, 2),
            'particle_count': particle_count,
            'scratch_count': scratch_count,
            'pattern_defect_count': pattern_defect_count,
            'total_defect_count': total_defects
        })
    return records


def generate_spc_data(num_wafers=NUM_WAFERS):
    """
    生成SPC (Statistical Process Control) 数据
    监控光刻工序的关键参数: CD(关键尺寸), Overlay(套刻精度)
    模拟从wafer 10开始, 光刻机参数开始漂移
    """
    records = []
    for w in range(1, num_wafers + 1):
        # CD目标值: 28nm
        cd_target = 28.0
        cd_ucl = 29.5
        cd_lcl = 26.5

        # Overlay目标值: 0nm
        ov_target = 0.0
        ov_ucl = 3.0
        ov_lcl = -3.0

        # wafer 10之后参数开始漂移
        if w >= 10:
            drift = 0.15 * (w - 9)
            cd_mean = cd_target + drift * 0.3
            ov_mean = ov_target + drift * 0.5
        else:
            cd_mean = cd_target
            ov_mean = ov_target

        cd_value = cd_mean + np.random.normal(0, 0.4)
        ov_value = ov_mean + np.random.normal(0, 0.8)

        cd_ooc = 1 if (cd_value > cd_ucl or cd_value < cd_lcl) else 0
        ov_ooc = 1 if (ov_value > ov_ucl or ov_value < ov_lcl) else 0

        records.append({
            'wafer_id': w,
            'CD_nm': round(cd_value, 3),
            'CD_target': cd_target,
            'CD_UCL': cd_ucl,
            'CD_LCL': cd_lcl,
            'CD_OOC': cd_ooc,
            'Overlay_nm': round(ov_value, 3),
            'Overlay_target': ov_target,
            'Overlay_UCL': ov_ucl,
            'Overlay_LCL': ov_lcl,
            'Overlay_OOC': ov_ooc
        })
    return records


def generate_alarm_data(spc_data, num_wafers=NUM_WAFERS):
    """
    基于SPC数据生成告警记录
    """
    records = []
    alarm_id = 1

    for row in spc_data:
        w = row['wafer_id']
        if row['CD_OOC']:
            records.append({
                'alarm_id': alarm_id,
                'wafer_id': w,
                'alarm_type': 'SPC_OOC',
                'parameter': 'CD',
                'value': row['CD_nm'],
                'spec_limit': f"[{row['CD_LCL']}, {row['CD_UCL']}]",
                'severity': 'WARNING' if abs(row['CD_nm'] - row['CD_target']) < 2.0 else 'CRITICAL',
                'equipment': 'LITHO-01',
                'step': 'Lithography'
            })
            alarm_id += 1

        if row['Overlay_OOC']:
            records.append({
                'alarm_id': alarm_id,
                'wafer_id': w,
                'alarm_type': 'SPC_OOC',
                'parameter': 'Overlay',
                'value': row['Overlay_nm'],
                'spec_limit': f"[{row['Overlay_LCL']}, {row['Overlay_UCL']}]",
                'severity': 'WARNING' if abs(row['Overlay_nm']) < 4.0 else 'CRITICAL',
                'equipment': 'LITHO-01',
                'step': 'Lithography'
            })
            alarm_id += 1

    # 添加良率告警
    for w in [3, 7, 12, 18, 22]:
        records.append({
            'alarm_id': alarm_id,
            'wafer_id': w,
            'alarm_type': 'YIELD_LOW',
            'parameter': 'Bin1_Yield',
            'value': round(np.random.uniform(0.78, 0.85), 3),
            'spec_limit': '>= 0.90',
            'severity': 'CRITICAL',
            'equipment': 'LITHO-01',
            'step': 'Final_Test'
        })
        alarm_id += 1

    return records


def main():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("半导体良率分析 - 数据生成")
    print("=" * 60)

    # 生成die坐标
    dies = generate_die_coordinates()
    print(f"晶圆die数量: {len(dies)}")

    # 生成各wafer数据
    all_yield = []
    all_wat = []
    all_defect = []

    for w in range(1, NUM_WAFERS + 1):
        all_yield.extend(generate_yield_map(dies, w))
        all_wat.extend(generate_wat_data(dies, w))
        all_defect.extend(generate_defect_data(dies, w))

    # 保存数据
    df_yield = pd.DataFrame(all_yield)
    df_yield.to_csv(os.path.join(output_dir, 'yield_bin_map.csv'), index=False)
    print(f"良率Bin Map数据: {len(df_yield)} 条 -> yield_bin_map.csv")

    df_wat = pd.DataFrame(all_wat)
    df_wat.to_csv(os.path.join(output_dir, 'wat_data.csv'), index=False)
    print(f"WAT测试数据: {len(df_wat)} 条 -> wat_data.csv")

    df_defect = pd.DataFrame(all_defect)
    df_defect.to_csv(os.path.join(output_dir, 'defect_data.csv'), index=False)
    print(f"缺陷检测数据: {len(df_defect)} 条 -> defect_data.csv")

    spc_data = generate_spc_data()
    df_spc = pd.DataFrame(spc_data)
    df_spc.to_csv(os.path.join(output_dir, 'spc_data.csv'), index=False)
    print(f"SPC监控数据: {len(df_spc)} 条 -> spc_data.csv")

    alarm_data = generate_alarm_data(spc_data)
    df_alarm = pd.DataFrame(alarm_data)
    df_alarm.to_csv(os.path.join(output_dir, 'alarm_data.csv'), index=False)
    print(f"告警数据: {len(df_alarm)} 条 -> alarm_data.csv")

    # 汇总统计
    print("\n" + "=" * 60)
    print("数据汇总统计")
    print("=" * 60)

    for w in range(1, NUM_WAFERS + 1):
        w_data = df_yield[df_yield['wafer_id'] == w]
        y = w_data['bin'].mean()
        flag = " *** LOW YIELD ***" if y < 0.90 else ""
        print(f"  Wafer {w:2d}: 良率 {y:.1%} ({w_data['bin'].sum()}/{len(w_data)}){flag}")

    lot_yield = df_yield['bin'].mean()
    print(f"\n  Lot平均良率: {lot_yield:.1%}")
    print("=" * 60)


if __name__ == '__main__':
    main()
