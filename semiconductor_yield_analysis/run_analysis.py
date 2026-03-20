#!/usr/bin/env python3
"""
半导体良率根因分析 - 完整流水线
一键运行: 数据生成 -> Wafer Map绘制 -> 相关性分析 -> 根因报告
"""

import sys
import os
import time

# 将项目路径加入
sys.path.insert(0, os.path.dirname(__file__))

from tools import generate_data, wafer_map, correlation_analysis


def main():
    start = time.time()

    print("\n" + "#" * 60)
    print("#  半导体良率根因分析 Demo - 完整流水线")
    print("#  场景: 某批次晶圆良率异常, 智能体自动分析定位根因")
    print("#" * 60)

    # Step 1: 数据生成
    print("\n>>> STEP 1/3: Generating Synthetic Data...")
    generate_data.main()

    # Step 2: Wafer Map 绘制
    print("\n>>> STEP 2/3: Drawing Wafer Maps...")
    wafer_map.main()

    # Step 3: 相关性分析与根因识别
    print("\n>>> STEP 3/3: Correlation Analysis & Root Cause Identification...")
    correlation_analysis.main()

    elapsed = time.time() - start
    print("\n" + "#" * 60)
    print(f"#  Pipeline completed in {elapsed:.1f} seconds")
    print("#" * 60)

    # 列出所有输出文件
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    files = sorted(os.listdir(output_dir))
    print(f"\nGenerated {len(files)} output files in {output_dir}/:")
    for f in files:
        size = os.path.getsize(os.path.join(output_dir, f))
        print(f"  {f:<45s} ({size / 1024:.1f} KB)")


if __name__ == '__main__':
    main()
