from prefect import get_client
from prefect.server.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterName,
    LogFilter,
    LogFilterFlowRunId,
)

from marvin.plugins import plugin
from marvin.utilities.strings import slice_tokens


@plugin
async def review_flow_run(flow_run_name: str, token_limit: int = 3000) -> str:
    """Retrieve and inspect logs from a Prefect flow run. The `flow_run_name`
    will always be of the form `adjective-animal`.
    """
    async with get_client() as client:
        flow_runs = await client.read_flow_runs(
            flow_run_filter=FlowRunFilter(name=FlowRunFilterName(like_=flow_run_name))
        )
        logs = await client.read_logs(
            log_filter=LogFilter(flow_run_id=LogFilterFlowRunId(any_=[flow_runs[0].id]))
        )

        log_str = "\n".join([log.message for log in logs])

        return slice_tokens(log_str[::-1], token_limit)[::-1]
