"""Render the ticket-statistics payload into Telegram-HTML message chunks.

The service returns a nested dict (sales / sold / usage). We build a flat list of
HTML lines, then pack them into messages that stay under Telegram's 4096-char
cap — splitting only on line boundaries so a single ticket figure is never cut in
half. Every field is read defensively (`.get`, `or {}`): the bot must not crash
if the service omits a section or sends a partial body.
"""
from collections.abc import Iterable

from app.tickets.prefixes import prefix_name

# Telegram rejects messages over 4096 chars; pack below that with headroom for
# the trailing newline accounting and any future prefix.
_CHUNK_LIMIT = 3900

# Non-breaking thin-ish separator for thousands so groups don't wrap awkwardly.
_THOUSANDS = " "


def _int(value: object) -> str:
    try:
        return f"{int(value):,}".replace(",", _THOUSANDS)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(value)


def _money(value: object) -> str:
    try:
        return f"{float(value):,.2f}".replace(",", _THOUSANDS)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(value)


def _counts(mapping: object) -> str:
    """Render a {label: count} mapping as indented bullet lines.

    Defensive: the service may nest a plain number where we expected a
    breakdown, so a scalar is rendered directly instead of crashing on .items().
    """
    if isinstance(mapping, dict):
        return "\n".join(f"     - {key}: {_int(count)}" for key, count in mapping.items())
    return f"     - {_int(mapping)}"


def _sales_block(sales: dict) -> list[str]:
    out = ["", "💰 <b>Продажи</b>", f"Операций: {_int(sales.get('count', 0))}"]
    for currency, info in (sales.get("by_currency") or {}).items():
        info = info or {}
        out.append(
            f"  {currency}: {_int(info.get('count', 0))} шт · "
            f"{_money(info.get('amount', 0))} "
            f"(зачислено {_money(info.get('settl_amount', 0))})"
        )
    return out


def _sold_block(sold: dict) -> list[str]:
    out = ["", f"🎟 <b>Выдано билетов: {_int(sold.get('total', 0))}</b>"]
    by_prefix = sold.get("by_prefix") or {}
    if by_prefix:
        out.append("<b>По префиксам:</b>")
        for prefix, info in by_prefix.items():
            info = info or {}
            out.append(f"  {prefix} · {prefix_name(prefix)}: {_int(info.get('total', 0))}")
            parts = info.get("parts") or {}
            if parts:
                out.append("" + _counts(parts))
    by_part = sold.get("by_part") or {}
    if by_part:
        out.append("<b>По номиналам:</b>")
        out.append("" + _counts(by_part))
    return out


def _day_lines(title: str, by_day: dict) -> list[str]:
    out = [f"<b>{title}:</b>"]
    for day in sorted(by_day):
        value = by_day[day]
        if isinstance(value, dict):
            if value:
                out.append(f"  {day}:")
                out.append(_counts(value))
            else:
                out.append(f"  {day}: —")
        else:
            # A plain number for the whole day (no per-prefix breakdown).
            out.append(f"  {day}: {_int(value)}")
    return out


def _usage_block(usage: dict) -> list[str]:
    out = ["", f"🚪 <b>Использование: {_int(usage.get('total', 0))}</b>"]
    by_day = usage.get("by_day") or {}
    if by_day:
        out += _day_lines("По дням", by_day)
    outside = usage.get("outside_window") or {}
    if outside:
        out += _day_lines("Вне периода фестиваля", outside)
    return out


def _chunk(lines: Iterable[str]) -> list[str]:
    """Pack lines into messages, each ≤ _CHUNK_LIMIT, splitting on line breaks."""
    messages: list[str] = []
    buffer: list[str] = []
    size = 0
    for line in lines:
        added = len(line) + 1  # + newline
        if buffer and size + added > _CHUNK_LIMIT:
            messages.append("\n".join(buffer))
            buffer, size = [], 0
        buffer.append(line)
        size += added
    if buffer:
        messages.append("\n".join(buffer))
    return messages


def format_stats(data: dict) -> list[str]:
    """Turn the raw stats dict into a list of Telegram-HTML messages."""
    lines = ["📊 <b>Статистика билетов</b>"]
    lines += _sales_block(data.get("sales") or {})
    lines += _sold_block(data.get("sold") or {})
    lines += _usage_block(data.get("usage") or {})
    return _chunk(lines)
