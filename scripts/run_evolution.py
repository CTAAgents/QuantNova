#!/usr/bin/env python3
"""
运行进化管理器进行策略优化
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

# 导入进化管理器
from evolution_tools.evolution_manager import EvolutionManager
from core.memory.experience import ExperienceMemory

def main():
    print("=" * 80)
    print("QuantNova 进化管理器 - 策略优化")
    print("=" * 80)
    print()
    
    # 创建经验记忆池
    experience_memory = ExperienceMemory(db_path=str(project_root / "data" / "experience.db"))
    
    # 创建进化管理器
    evolution_manager = EvolutionManager(
        experience_memory=experience_memory,
        db_path=str(project_root / "data" / "evolution.db")
    )
    
    print("1. 进化状态检查")
    print("-" * 40)
    status = evolution_manager.get_evolution_status()
    print(f"   - 进化次数: {status.get('evolution_count', 0)}")
    print(f"   - 上次进化: {status.get('last_evolution_time', '从未')}")
    print(f"   - 经验总数: {status.get('total_experiences', 0)}")
    print()
    
    print("2. 经验统计")
    print("-" * 40)
    stats = evolution_manager.get_experience_stats()
    print(f"   - 总经验数: {stats.get('total_experiences', 0)}")
    print(f"   - 阶段分布: {stats.get('phase_distribution', {})}")
    print(f"   - 动作分布: {stats.get('action_distribution', {})}")
    print(f"   - 总体胜率: {stats.get('overall_win_rate', 0):.2%}")
    print()
    
    print("3. 执行进化流程")
    print("-" * 40)
    print("   - 触发原因: 手动触发 - 策略优化")
    print("   - 执行进化...")
    
    try:
        result = evolution_manager.run_evolution(reason="手动触发 - 策略优化")
        
        print("   - 进化结果:")
        if result.get("success"):
            print(f"     * 进化成功: {result.get('success', False)}")
            print(f"     * 优化建议: {result.get('optimization_suggestions', [])}")
            print(f"     * 规则晋升: {result.get('promoted_rules', [])}")
            print(f"     * 策略适配: {result.get('strategy_adaptations', [])}")
        else:
            print(f"     * 进化失败: {result.get('error', '未知错误')}")
    except Exception as e:
        print(f"   - 进化失败: {e}")
    
    print()
    print("4. 进化后状态")
    print("-" * 40)
    status_after = evolution_manager.get_evolution_status()
    print(f"   - 进化次数: {status_after.get('evolution_count', 0)}")
    print(f"   - 上次进化: {status_after.get('last_evolution_time', '从未')}")
    print(f"   - 经验总数: {status_after.get('total_experiences', 0)}")
    print()
    
    print("5. 优化建议")
    print("-" * 40)
    print("   - 基于进化结果，建议以下优化:")
    print("   - 1. 记录每次多空判断的准确率")
    print("   - 2. 分析成功和失败案例的特征")
    print("   - 3. 优化指标权重和阈值")
    print("   - 4. 定期运行进化流程")
    print("   - 5. 监控过拟合风险")
    print()
    
    print("=" * 80)
    print("进化流程完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
