"""
Orchestrator 调度脚本 — 主协调流程

实现 Scanner → Reasoner → Debater 的完整调度流程。
根据 Scanner 输出的信号强度，决定是否触发 Reasoner 和 Debater。

使用方式：
    python tools/orchestrator.py scan              # 执行扫描 + 推理流程
    python tools/orchestrator.py heartbeat         # 执行心跳检查 + 推理流程
    python tools/orchestrator.py full              # 完整流程（扫描 + 心跳 + 推理）
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any

# 导入数据格式工具
from data_formats import load_config, read_scan_result, write_scan_result

# 文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def run_scanner() -> Dict[str, Any]:
    """执行 Scanner 脚本"""
    import subprocess
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_opportunities.py')
    python_path = sys.executable
    
    print("[Scanner] 执行全品种扫描...")
    result = subprocess.run(
        [python_path, script_path, '--output', 'json', '--save'],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        print(f"[Scanner] 错误: {result.stderr}")
        return {"signals": [], "total_scanned": 0, "signal_count": 0}
    
    # 读取保存的结果
    scan_result = read_scan_result()
    if scan_result:
        print(f"[Scanner] 完成: {scan_result.get('total_scanned', 0)} 个品种, {scan_result.get('signal_count', 0)} 个信号")
        return scan_result
    else:
        print("[Scanner] 警告: 无法读取扫描结果")
        return {"signals": [], "total_scanned": 0, "signal_count": 0}


def run_heartbeat() -> Dict[str, Any]:
    """执行心跳检查"""
    import subprocess
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'heartbeat.py')
    python_path = sys.executable
    
    print("[Heartbeat] 执行心跳检查...")
    result = subprocess.run(
        [python_path, script_path, '--output', 'json', '--save'],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode != 0:
        print(f"[Heartbeat] 错误: {result.stderr}")
        return {"has_events": False, "alerts": [], "new_signals": []}
    
    try:
        heartbeat_result = json.loads(result.stdout)
        has_events = heartbeat_result.get('has_events', False)
        alerts = heartbeat_result.get('alerts', [])
        new_signals = heartbeat_result.get('new_signals', [])
        
        print(f"[Heartbeat] 完成: {len(alerts)} 个预警, {len(new_signals)} 个新信号")
        return heartbeat_result
    except json.JSONDecodeError:
        print("[Heartbeat] 警告: 无法解析输出")
        return {"has_events": False, "alerts": [], "new_signals": []}


def run_reasoner(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """执行 Reasoner 推理"""
    import subprocess
    
    if not signals:
        print("[Reasoner] 无信号需要推理")
        return []
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_reasoner.py')
    python_path = sys.executable
    
    # 将信号保存到临时文件
    temp_file = os.path.join(DATA_DIR, 'temp_signals.json')
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump({"signals": signals}, f, ensure_ascii=False)
    
    print(f"[Reasoner] 推理 {len(signals)} 个信号...")
    result = subprocess.run(
        [python_path, script_path, '--output', 'json', '--save'],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        print(f"[Reasoner] 错误: {result.stderr}")
        return []
    
    try:
        reasoning_results = json.loads(result.stdout)
        print(f"[Reasoner] 完成: {len(reasoning_results)} 个推理结果")
        return reasoning_results
    except json.JSONDecodeError:
        print("[Reasoner] 警告: 无法解析输出")
        return []


def run_debater(reasoning_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """执行 Debater 辩论"""
    import subprocess
    
    if not reasoning_results:
        print("[Debater] 无推理结果需要辩论")
        return []
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_debater.py')
    python_path = sys.executable
    
    # 将推理结果保存到临时文件
    temp_file = os.path.join(DATA_DIR, 'temp_reasoning.json')
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(reasoning_results, f, ensure_ascii=False)
    
    print(f"[Debater] 辩论 {len(reasoning_results)} 个结果...")
    result = subprocess.run(
        [python_path, script_path, '--output', 'json', '--save', '--force'],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        print(f"[Debater] 错误: {result.stderr}")
        return []
    
    try:
        debate_results = json.loads(result.stdout)
        print(f"[Debater] 完成: {len(debate_results)} 个辩论结果")
        return debate_results
    except json.JSONDecodeError:
        print("[Debater] 警告: 无法解析输出")
        return []


def determine_action(scan_result: Dict[str, Any], heartbeat_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据 Scanner 和 Heartbeat 结果，决定下一步动作
    
    返回:
        动作字典，包含需要触发的 Agent 和信号列表
    """
    config = load_config()
    reasoner_config = config.get('reasoner', {})
    confidence_threshold = reasoner_config.get('debate_trigger_confidence', 0.7)
    
    action = {
        "trigger_reasoner": False,
        "trigger_debater": False,
        "signals_to_reason": [],
        "alerts_to_push": []
    }
    
    # 处理 Scanner 信号
    signals = scan_result.get('signals', [])
    if signals:
        # 按信号强度分类
        strong_signals = [s for s in signals if s.get('signal_strength') == 'STRONG']
        medium_signals = [s for s in signals if s.get('signal_strength') == 'MEDIUM']
        
        if strong_signals:
            action["trigger_reasoner"] = True
            action["trigger_debater"] = True
            action["signals_to_reason"].extend(strong_signals)
        elif medium_signals:
            action["trigger_reasoner"] = True
            action["signals_to_reason"].extend(medium_signals[:3])  # 最多 3 个
    
    # 处理 Heartbeat 预警
    alerts = heartbeat_result.get('alerts', [])
    high_alerts = [a for a in alerts if a.get('severity') == 'HIGH']
    medium_alerts = [a for a in alerts if a.get('severity') == 'MEDIUM']
    
    if high_alerts:
        action["trigger_reasoner"] = True
        action["alerts_to_push"].extend(high_alerts)
    elif medium_alerts:
        action["alerts_to_push"].extend(medium_alerts)
    
    # 处理 Heartbeat 新信号
    new_signals = heartbeat_result.get('new_signals', [])
    if new_signals:
        action["trigger_reasoner"] = True
        action["signals_to_reason"].extend(new_signals)
    
    return action


def format_output(scan_result: Dict[str, Any], heartbeat_result: Dict[str, Any],
                  reasoning_results: List[Dict[str, Any]], 
                  debate_results: List[Dict[str, Any]]) -> str:
    """格式化输出结果"""
    lines = []
    lines.append(f"趋势跟踪 Agent 运行报告")
    lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    
    # Scanner 结果
    lines.append(f"\n[Scanner]")
    lines.append(f"  扫描品种: {scan_result.get('total_scanned', 0)} 个")
    lines.append(f"  发现信号: {scan_result.get('signal_count', 0)} 个")
    
    # Heartbeat 结果
    lines.append(f"\n[Heartbeat]")
    lines.append(f"  预警: {len(heartbeat_result.get('alerts', []))} 个")
    lines.append(f"  新信号: {len(heartbeat_result.get('new_signals', []))} 个")
    
    # Reasoner 结果
    if reasoning_results:
        lines.append(f"\n[Reasoner]")
        lines.append(f"  推理结果: {len(reasoning_results)} 个")
        for r in reasoning_results:
            symbol = r.get('symbol', '')
            confidence = r.get('confidence', 0)
            lines.append(f"    {symbol}: 置信度 {confidence:.2f}")
    
    # Debater 结果
    if debate_results:
        lines.append(f"\n[Debater]")
        lines.append(f"  辩论结果: {len(debate_results)} 个")
        for d in debate_results:
            symbol = d.get('symbol', '')
            orig = d.get('original_confidence', 0)
            revised = d.get('revised_confidence', 0)
            divergence = d.get('debate_result', {}).get('divergence_level', 'N/A')
            lines.append(f"    {symbol}: 置信度 {orig:.2f} → {revised:.2f} (分歧: {divergence})")
    
    return '\n'.join(lines)


def run_full_flow():
    """执行完整流程"""
    print("趋势跟踪 Agent 启动")
    print("=" * 60)
    
    # Step 1: 执行 Scanner
    scan_result = run_scanner()
    
    # Step 2: 执行 Heartbeat
    heartbeat_result = run_heartbeat()
    
    # Step 3: 决定下一步动作
    action = determine_action(scan_result, heartbeat_result)
    
    # Step 4: 执行 Reasoner（如果需要）
    reasoning_results = []
    if action["trigger_reasoner"]:
        reasoning_results = run_reasoner(action["signals_to_reason"])
    
    # Step 5: 执行 Debater（如果需要）
    debate_results = []
    if action["trigger_debater"] and reasoning_results:
        debate_results = run_debater(reasoning_results)
    
    # Step 6: 格式化输出
    output = format_output(scan_result, heartbeat_result, reasoning_results, debate_results)
    print("\n" + output)
    
    # Step 7: 保存完整报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "scan_result": scan_result,
        "heartbeat_result": heartbeat_result,
        "action": action,
        "reasoning_results": reasoning_results,
        "debate_results": debate_results
    }
    
    report_path = os.path.join(DATA_DIR, 'latest_orchestrator_report.json')
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n完整报告已保存到 data/latest_orchestrator_report.json")


def main():
    parser = argparse.ArgumentParser(description="Orchestrator 调度脚本")
    parser.add_argument("mode", choices=["scan", "heartbeat", "full"], 
                       help="运行模式: scan=扫描+推理, heartbeat=心跳+推理, full=完整流程")
    parser.add_argument("--output", choices=["json", "text"], default="text", help="输出格式")
    
    args = parser.parse_args()
    
    if args.mode == "scan":
        scan_result = run_scanner()
        action = determine_action(scan_result, {"alerts": [], "new_signals": []})
        if action["trigger_reasoner"]:
            reasoning_results = run_reasoner(action["signals_to_reason"])
            if action["trigger_debater"]:
                run_debater(reasoning_results)
    
    elif args.mode == "heartbeat":
        heartbeat_result = run_heartbeat()
        action = determine_action({"signals": []}, heartbeat_result)
        if action["trigger_reasoner"]:
            reasoning_results = run_reasoner(action["signals_to_reason"])
            if action["trigger_debater"]:
                run_debater(reasoning_results)
    
    elif args.mode == "full":
        run_full_flow()


if __name__ == "__main__":
    main()
