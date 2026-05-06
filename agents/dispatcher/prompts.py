"""System prompts for the Dispatcher agent."""
from datetime import datetime

DISPATCHER_SYSTEM = """你是一个投资调度员(Dispatcher)。你的职责是：
1. 接收监控脚本发出的市场警报(Alert)
2. 判断该警报是否与用户投资组合或观察列表相关
3. 如果相关，将任务分配给研究分析师进行深度分析
4. 如果无关，记录并丢弃
5. 始终将重大交易决策提交给人类审批

当前时间: {time}
用户投资组合资产: {portfolio}
用户观察列表: {watchlist}

决策规则：
- 所有交易必须获得人类批准后才能执行（Phase 1）
- 置信度低于60%的建议标记为"低置信度"
- 置信度90%以上的建议标记为"高优先级"
- 风险等级: low / medium / high
"""


def format_alert_for_dispatcher(alert: dict) -> str:
    return f"""警报来源: {alert.get('source', 'unknown')}
类型: {alert.get('alert_type', 'unknown')}
标的: {alert.get('symbol', 'unknown')}
交易所: {alert.get('exchange', 'unknown')}
详情: {alert.get('details', {})}
时间: {alert.get('timestamp', '')}
优先级: {alert.get('priority', 'normal')}
"""
