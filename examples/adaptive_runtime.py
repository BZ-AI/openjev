"""Local-first OpenJev v0.2 example.

Install the optional local backend first:

    pip install -e ".[laya]"

Set TYPESAFE_API_KEY only if you want the strong Jev fallback.
"""

import os

from openjev import AdaptiveDecisionRuntime, Choice, OpenJev, RoutingPolicy
from openjev.providers import JevProvider, LayaProvider

fast = OpenJev(LayaProvider())
strong = None
if os.environ.get("TYPESAFE_API_KEY"):
    strong = OpenJev(JevProvider())

runtime = AdaptiveDecisionRuntime(
    fast,
    strong,
    policy=RoutingPolicy(confidence_threshold=0.60, max_fast_choice_options=20),
    fast_name="Laya local",
    strong_name="Jev hosted",
)

result = runtime.evaluate(
    state={"message": "我要退款，东西还没发货。"},
    questions={
        "intent": Choice(
            instructions="这条客服消息主要应该由哪个部门处理？",
            criteria={
                "billing": "账单、退款、付款、发票",
                "logistics": "物流、发货、快递、收货",
                "tech": "技术故障、报错、登录问题",
                "sales": "售前咨询、购买意向、演示",
            },
        )
    },
)

print(result.model_dump_json(indent=2))
