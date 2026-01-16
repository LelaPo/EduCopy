"""
Форматирование домашних заданий для Telegram.
"""
from datetime import date
from collections import defaultdict
from app.services.authedu_client import HomeworkItem


def format_homework_list(
    items: list[HomeworkItem], 
    target_date: date,
    is_range: bool = False,
) -> str:
    """
    Отформатировать список ДЗ для отправки в Telegram.
    """
    if not items:
        date_str = target_date.strftime("%d.%m.%Y")
        if is_range:
            return "📭 На этот период ДЗ не найдено."
        return f"📭 На {date_str} ДЗ не найдено."
    
    lines = []
    
    if is_range:
        # Группируем по датам
        by_date: dict[date, list[HomeworkItem]] = defaultdict(list)
        for item in items:
            by_date[item.homework_date].append(item)
        
        lines.append("📚 <b>Домашние задания:</b>\n")
        
        for hw_date in sorted(by_date.keys()):
            date_str = hw_date.strftime("%d.%m.%Y")
            weekday = get_weekday_name(hw_date)
            lines.append(f"━━━ <b>{date_str} ({weekday})</b> ━━━")
            
            for item in by_date[hw_date]:
                lines.append(format_single_homework(item))
            lines.append("")
    else:
        date_str = target_date.strftime("%d.%m.%Y")
        weekday = get_weekday_name(target_date)
        lines.append(f"📚 <b>ДЗ на {date_str} ({weekday}):</b>\n")
        
        for item in items:
            lines.append(format_single_homework(item))
    
    return "\n".join(lines)


def format_single_homework(item: HomeworkItem) -> str:
    """Форматировать одно ДЗ."""
    lines = []
    
    # Статус и предмет
    done_icon = "✅" if item.is_done else "📖"
    lines.append(f"{done_icon} <b>{item.subject}</b>")
    
    # Текст ДЗ (ограничиваем длину)
    hw_text = item.homework_text[:800]
    if len(item.homework_text) > 800:
        hw_text += "..."
    lines.append(f"   {hw_text}")
    
    # Материалы — просто "Файл 1", "Файл 2"
    if item.materials:
        for i, mat in enumerate(item.materials[:5], 1):
            lines.append(f"   📎 <a href=\"{mat.url}\">Файл {i}</a>")
    
    return "\n".join(lines)


def get_weekday_name(d: date) -> str:
    """Получить название дня недели на русском."""
    weekdays = [
        "пн", "вт", "ср", "чт", "пт", "сб", "вс"
    ]
    return weekdays[d.weekday()]
