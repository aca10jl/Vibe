"""
半导体良率分析 - Wafer Map 绘制工具
支持绘制: Bin Map, WAT参数Map, Defect Map, 热力图等
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.collections import PatchCollection
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

WAFER_DIAMETER = 300
DIE_SIZE = 10


def draw_wafer_outline(ax, color='black', lw=1.5):
    """绘制晶圆轮廓和notch"""
    circle = plt.Circle((0, 0), WAFER_DIAMETER / 2, fill=False,
                         edgecolor=color, linewidth=lw)
    ax.add_patch(circle)
    # notch标记
    notch_y = -WAFER_DIAMETER / 2
    ax.plot([-3, 0, 3], [notch_y, notch_y + 5, notch_y], color=color, lw=lw)


def plot_bin_map(df_wafer, wafer_id, output_path=None):
    """绘制单片wafer的Bin Map (Pass/Fail)"""
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    data = df_wafer[df_wafer['wafer_id'] == wafer_id]
    total = len(data)
    passed = data['bin'].sum()
    yield_pct = passed / total * 100

    cmap = ListedColormap(['#FF4444', '#44BB44'])  # Fail=红, Pass=绿

    rects = []
    colors = []
    for _, row in data.iterrows():
        rect = patches.Rectangle(
            (row['center_x_mm'] - DIE_SIZE / 2, row['center_y_mm'] - DIE_SIZE / 2),
            DIE_SIZE - 0.5, DIE_SIZE - 0.5
        )
        rects.append(rect)
        colors.append(row['bin'])

    pc = PatchCollection(rects, cmap=cmap, edgecolors='gray', linewidths=0.3)
    pc.set_array(np.array(colors))
    pc.set_clim(0, 1)
    ax.add_collection(pc)

    draw_wafer_outline(ax)

    ax.set_xlim(-WAFER_DIAMETER / 2 - 10, WAFER_DIAMETER / 2 + 10)
    ax.set_ylim(-WAFER_DIAMETER / 2 - 15, WAFER_DIAMETER / 2 + 10)
    ax.set_aspect('equal')
    ax.set_title(f'Wafer #{wafer_id} Bin Map\nYield: {yield_pct:.1f}% ({passed}/{total})',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')

    # 图例
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='#44BB44', label=f'Pass ({passed})'),
                       Patch(facecolor='#FF4444', label=f'Fail ({total - passed})')]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=11)

    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {output_path}")
    plt.close(fig)
    return fig


def plot_heatmap(df_wafer, wafer_id, value_col, title_label, cmap_name='RdYlGn_r',
                 output_path=None, vmin=None, vmax=None):
    """绘制参数热力图 (通用)"""
    fig, ax = plt.subplots(1, 1, figsize=(9, 8))

    data = df_wafer[df_wafer['wafer_id'] == wafer_id]
    values = data[value_col].values

    if vmin is None:
        vmin = np.percentile(values, 2)
    if vmax is None:
        vmax = np.percentile(values, 98)

    norm = Normalize(vmin=vmin, vmax=vmax)

    rects = []
    color_vals = []
    for _, row in data.iterrows():
        rect = patches.Rectangle(
            (row['center_x_mm'] - DIE_SIZE / 2, row['center_y_mm'] - DIE_SIZE / 2),
            DIE_SIZE - 0.5, DIE_SIZE - 0.5
        )
        rects.append(rect)
        color_vals.append(row[value_col])

    pc = PatchCollection(rects, cmap=cmap_name, edgecolors='gray',
                         linewidths=0.2, norm=norm)
    pc.set_array(np.array(color_vals))
    ax.add_collection(pc)

    draw_wafer_outline(ax)

    ax.set_xlim(-WAFER_DIAMETER / 2 - 10, WAFER_DIAMETER / 2 + 10)
    ax.set_ylim(-WAFER_DIAMETER / 2 - 15, WAFER_DIAMETER / 2 + 10)
    ax.set_aspect('equal')
    ax.set_title(f'Wafer #{wafer_id} - {title_label}', fontsize=14, fontweight='bold')
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')

    cbar = plt.colorbar(pc, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label(title_label, fontsize=11)

    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {output_path}")
    plt.close(fig)
    return fig


def plot_stacked_wafer_map(df_wafer, wafer_ids, value_col, title_label,
                           cmap_name='RdYlGn_r', output_path=None):
    """绘制多片wafer的对比图 (2行排列)"""
    n = len(wafer_ids)
    ncols = min(5, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 4.2 * nrows))

    if nrows == 1 and ncols == 1:
        axes = np.array([[axes]])
    elif nrows == 1:
        axes = axes.reshape(1, -1)
    elif ncols == 1:
        axes = axes.reshape(-1, 1)

    all_vals = df_wafer[df_wafer['wafer_id'].isin(wafer_ids)][value_col]
    vmin = np.percentile(all_vals, 2)
    vmax = np.percentile(all_vals, 98)
    norm = Normalize(vmin=vmin, vmax=vmax)

    for idx, wid in enumerate(wafer_ids):
        r, c = divmod(idx, ncols)
        ax = axes[r][c]
        data = df_wafer[df_wafer['wafer_id'] == wid]

        rects = []
        color_vals = []
        for _, row in data.iterrows():
            rect = patches.Rectangle(
                (row['center_x_mm'] - DIE_SIZE / 2, row['center_y_mm'] - DIE_SIZE / 2),
                DIE_SIZE - 0.5, DIE_SIZE - 0.5
            )
            rects.append(rect)
            color_vals.append(row[value_col])

        pc = PatchCollection(rects, cmap=cmap_name, edgecolors='gray',
                             linewidths=0.1, norm=norm)
        pc.set_array(np.array(color_vals))
        ax.add_collection(pc)

        circle = plt.Circle((0, 0), WAFER_DIAMETER / 2, fill=False,
                             edgecolor='black', linewidth=1)
        ax.add_patch(circle)
        ax.set_xlim(-160, 160)
        ax.set_ylim(-165, 155)
        ax.set_aspect('equal')

        if value_col == 'bin':
            y_val = data[value_col].mean() * 100
            ax.set_title(f'W{wid} (Y:{y_val:.1f}%)', fontsize=10)
        else:
            ax.set_title(f'Wafer {wid}', fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])

    # 隐藏空白子图
    for idx in range(len(wafer_ids), nrows * ncols):
        r, c = divmod(idx, ncols)
        axes[r][c].set_visible(False)

    fig.suptitle(f'{title_label} - Multi-Wafer Comparison', fontsize=14, fontweight='bold')
    fig.subplots_adjust(right=0.92)
    cbar_ax = fig.add_axes([0.94, 0.15, 0.02, 0.7])
    sm = plt.cm.ScalarMappable(cmap=cmap_name, norm=norm)
    fig.colorbar(sm, cax=cbar_ax, label=title_label)

    plt.tight_layout(rect=[0, 0, 0.93, 0.95])
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {output_path}")
    plt.close(fig)
    return fig


def plot_spc_chart(df_spc, output_path=None):
    """绘制SPC控制图 (CD和Overlay)"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    wafers = df_spc['wafer_id']

    # CD控制图
    ax1.plot(wafers, df_spc['CD_nm'], 'bo-', markersize=6, label='CD')
    ax1.axhline(y=df_spc['CD_target'].iloc[0], color='green', linestyle='-',
                linewidth=2, label='Target')
    ax1.axhline(y=df_spc['CD_UCL'].iloc[0], color='red', linestyle='--',
                linewidth=1.5, label='UCL')
    ax1.axhline(y=df_spc['CD_LCL'].iloc[0], color='red', linestyle='--',
                linewidth=1.5, label='LCL')

    ooc_cd = df_spc[df_spc['CD_OOC'] == 1]
    ax1.scatter(ooc_cd['wafer_id'], ooc_cd['CD_nm'], color='red', s=100,
                zorder=5, marker='X', label='OOC')

    ax1.set_title('SPC Control Chart - Critical Dimension (CD)', fontsize=13, fontweight='bold')
    ax1.set_xlabel('Wafer ID')
    ax1.set_ylabel('CD (nm)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(wafers)

    # Overlay控制图
    ax2.plot(wafers, df_spc['Overlay_nm'], 'rs-', markersize=6, label='Overlay')
    ax2.axhline(y=df_spc['Overlay_target'].iloc[0], color='green', linestyle='-',
                linewidth=2, label='Target')
    ax2.axhline(y=df_spc['Overlay_UCL'].iloc[0], color='red', linestyle='--',
                linewidth=1.5, label='UCL')
    ax2.axhline(y=df_spc['Overlay_LCL'].iloc[0], color='red', linestyle='--',
                linewidth=1.5, label='LCL')

    ooc_ov = df_spc[df_spc['Overlay_OOC'] == 1]
    ax2.scatter(ooc_ov['wafer_id'], ooc_ov['Overlay_nm'], color='darkred', s=100,
                zorder=5, marker='X', label='OOC')

    ax2.set_title('SPC Control Chart - Overlay', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Wafer ID')
    ax2.set_ylabel('Overlay (nm)')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(wafers)

    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {output_path}")
    plt.close(fig)
    return fig


def plot_defect_scatter_map(df_defect, wafer_id, output_path=None):
    """绘制缺陷散点图 (不同类型不同颜色)"""
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    data = df_defect[df_defect['wafer_id'] == wafer_id]

    # 背景: 晶圆轮廓
    draw_wafer_outline(ax, color='gray')

    # 根据缺陷数量绘制散点
    for _, row in data.iterrows():
        cx, cy = row['center_x_mm'], row['center_y_mm']
        if row['particle_count'] > 0:
            for _ in range(int(row['particle_count'])):
                ox = np.random.uniform(-3, 3)
                oy = np.random.uniform(-3, 3)
                ax.plot(cx + ox, cy + oy, 'o', color='blue', markersize=3, alpha=0.6)

        if row['scratch_count'] > 0:
            for _ in range(int(row['scratch_count'])):
                ox = np.random.uniform(-3, 3)
                oy = np.random.uniform(-3, 3)
                ax.plot(cx + ox, cy + oy, 's', color='orange', markersize=4, alpha=0.7)

        if row['pattern_defect_count'] > 0:
            for _ in range(int(row['pattern_defect_count'])):
                ox = np.random.uniform(-3, 3)
                oy = np.random.uniform(-3, 3)
                ax.plot(cx + ox, cy + oy, '^', color='red', markersize=4, alpha=0.7)

    ax.set_xlim(-WAFER_DIAMETER / 2 - 10, WAFER_DIAMETER / 2 + 10)
    ax.set_ylim(-WAFER_DIAMETER / 2 - 15, WAFER_DIAMETER / 2 + 10)
    ax.set_aspect('equal')

    total_p = data['particle_count'].sum()
    total_s = data['scratch_count'].sum()
    total_d = data['pattern_defect_count'].sum()

    ax.set_title(f'Wafer #{wafer_id} Defect Map\n'
                 f'Total: {total_p + total_s + total_d} '
                 f'(Particle:{total_p}, Scratch:{total_s}, Pattern:{total_d})',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='blue',
               markersize=8, label=f'Particle ({total_p})'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='orange',
               markersize=8, label=f'Scratch ({total_s})'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='red',
               markersize=8, label=f'Pattern Defect ({total_d})')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {output_path}")
    plt.close(fig)
    return fig


def main():
    """生成所有Wafer Map"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("半导体良率分析 - Wafer Map 绘制")
    print("=" * 60)

    # 加载数据
    df_yield = pd.read_csv(os.path.join(data_dir, 'yield_bin_map.csv'))
    df_wat = pd.read_csv(os.path.join(data_dir, 'wat_data.csv'))
    df_defect = pd.read_csv(os.path.join(data_dir, 'defect_data.csv'))
    df_spc = pd.read_csv(os.path.join(data_dir, 'spc_data.csv'))

    # 选择有代表性的wafer
    highlight_wafers = [1, 7, 12, 18, 25]

    # 1. Bin Map
    print("\n[1] Bin Map (Pass/Fail)")
    for wid in highlight_wafers:
        plot_bin_map(df_yield, wid,
                     os.path.join(output_dir, f'bin_map_wafer{wid}.png'))

    # 2. Bin Map 多片对比
    print("\n[2] Multi-Wafer Bin Map Comparison")
    compare_wafers = [1, 5, 7, 12, 18, 22, 25]
    plot_stacked_wafer_map(df_yield, compare_wafers, 'bin', 'Bin (Pass/Fail)',
                           cmap_name='RdYlGn',
                           output_path=os.path.join(output_dir, 'bin_map_comparison.png'))

    # 3. WAT参数Map
    print("\n[3] WAT Parameter Maps")
    for param, label, cmap in [
        ('Vth_V', 'Vth (V)', 'RdYlGn_r'),
        ('Idsat_uA', 'Idsat (uA)', 'RdYlGn'),
        ('Rs_ohm_sq', 'Rs (ohm/sq)', 'RdYlGn_r')
    ]:
        for wid in [1, 12]:
            plot_heatmap(df_wat, wid, param, label, cmap,
                         os.path.join(output_dir, f'wat_{param}_wafer{wid}.png'))

    # WAT多片对比
    for param, label, cmap in [
        ('Vth_V', 'Vth (V)', 'RdYlGn_r'),
        ('Rs_ohm_sq', 'Rs (ohm/sq)', 'RdYlGn_r')
    ]:
        plot_stacked_wafer_map(df_wat, compare_wafers, param, label,
                               cmap_name=cmap,
                               output_path=os.path.join(output_dir, f'wat_{param}_comparison.png'))

    # 4. Defect Map
    print("\n[4] Defect Maps")
    for wid in highlight_wafers:
        plot_defect_scatter_map(df_defect, wid,
                                os.path.join(output_dir, f'defect_map_wafer{wid}.png'))

    # Defect热力图
    print("\n[5] Defect Heatmap")
    plot_stacked_wafer_map(df_defect, compare_wafers, 'pattern_defect_count',
                           'Pattern Defect Count', cmap_name='YlOrRd',
                           output_path=os.path.join(output_dir, 'defect_pattern_comparison.png'))

    # 5. SPC控制图
    print("\n[6] SPC Control Charts")
    plot_spc_chart(df_spc, os.path.join(output_dir, 'spc_control_chart.png'))

    print("\n" + "=" * 60)
    print(f"所有Wafer Map已保存到: {output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
