from collections.abc import Iterable
from dataclasses import dataclass

from veil.engine.constants.prices import DEFAULT_MODEL_PRICES, PRICE_UNIT_TOKENS
from veil.engine.models.config.settings import Settings
from veil.engine.models.report.model_price import ModelPrice
from veil.engine.models.report.ticket_usage import ModelTokens, TicketUsage


@dataclass
class ModelCost:
    """The tokens of one model and what they cost. The costs are None when the model has no price."""

    uncached: int = 0
    cached: int = 0
    output: int = 0
    input_cost: float | None = 0.0
    output_cost: float | None = 0.0

    @property
    def total_cost(self) -> float | None:
        if self.input_cost is None or self.output_cost is None:
            return None
        return self.input_cost + self.output_cost


def price_table(settings: Settings) -> dict[str, ModelPrice]:
    """The price of each model: the default prices, then the prices of the settings on top."""
    defaults = {
        model: ModelPrice(input=i, cached_input=c, output=o)
        for model, (i, c, o) in DEFAULT_MODEL_PRICES.items()
    }
    return {**defaults, **settings.model_prices}


def cost_of(tokens: ModelTokens, price: ModelPrice | None) -> ModelCost:
    """The cost of the tokens of one model. `input` of the API holds the cached tokens, so they are taken out first."""
    uncached = max(tokens.input - tokens.cached, 0)
    if price is None:
        return ModelCost(uncached, tokens.cached, tokens.output, None, None)
    return ModelCost(
        uncached,
        tokens.cached,
        tokens.output,
        (uncached * price.input + tokens.cached * price.cached_input)
        / PRICE_UNIT_TOKENS,
        tokens.output * price.output / PRICE_UNIT_TOKENS,
    )


def cost_by_model(
    usages: Iterable[TicketUsage], prices: dict[str, ModelPrice]
) -> dict[str, ModelCost]:
    """Add the tokens of every ticket for each model, then price them. The models keep the order of first use."""
    summed: dict[str, ModelTokens] = {}
    for usage in usages:
        for model, tokens in usage.by_model.items():
            total = summed.setdefault(model, ModelTokens())
            total.input += tokens.input
            total.output += tokens.output
            total.cached += tokens.cached
    return {
        model: cost_of(tokens, prices.get(model)) for model, tokens in summed.items()
    }
