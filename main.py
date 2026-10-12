import html

from telebot import TeleBot, types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from config import DATABASE, TOKEN
from logic import PortfolioManager


if not TOKEN:
    raise ValueError(
        "Bitte tragen Sie den Telegram-Bot-Token in config.py ein."
    )

bot = TeleBot(TOKEN)
manager = PortfolioManager(DATABASE)
manager.create_tables()
manager.seed_defaults()

CANCEL = "Abbrechen 🚫"

UPDATE_FIELDS = {
    "Name": ("project_name", "Bitte gib den neuen Projektnamen ein:"),
    "Beschreibung": ("description", "Bitte gib die neue Beschreibung ein:"),
    "Repository": ("url", "Bitte gib den neuen Repository-Link ein:"),
    "Status": ("status_id", "Bitte wähle den neuen Status:"),
}


def cancel_markup():
    markup = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    markup.add(KeyboardButton(CANCEL))
    return markup


def reply_keyboard(items, include_cancel=True):
    markup = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    for item in items:
        markup.add(KeyboardButton(str(item)))
    if include_cancel:
        markup.add(KeyboardButton(CANCEL))
    return markup


def project_action_markup(project_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "✏️ Bearbeiten",
            callback_data=f"edit:{project_id}",
        ),
        InlineKeyboardButton(
            "🧠 Skills",
            callback_data=f"skills:{project_id}",
        ),
    )
    markup.row(
        InlineKeyboardButton(
            "🗑 Löschen",
            callback_data=f"delete:{project_id}",
        )
    )
    return markup


def project_filter_markup():
    markup = InlineKeyboardMarkup()
    statuses = ["Alle"] + [x[0] for x in manager.get_statuses()]

    for status in statuses:
        markup.add(
            InlineKeyboardButton(
                status,
                callback_data=f"filter:{status}",
            )
        )
    return markup


def format_project(project):
    project_id, name, description, url, status, created_at, updated_at = project
    skills = manager.get_project_skills(project_id)

    safe_name = html.escape(str(name))
    safe_description = html.escape(str(description or "—"))
    safe_url = html.escape(str(url or "—"))
    safe_status = html.escape(str(status))
    safe_created_at = html.escape(str(created_at))
    safe_updated_at = html.escape(str(updated_at))
    skills_text = (
        ", ".join(html.escape(str(skill)) for skill in skills)
        if skills
        else "Noch keine Technologien hinzugefügt"
    )

    return (
        f"📌 <b>{safe_name}</b>\n\n"
        f"📝 <b>Beschreibung:</b>\n{safe_description}\n\n"
        f"🔗 <b>Repository:</b>\n{safe_url}\n\n"
        f"📊 <b>Status:</b>\n{safe_status}\n\n"
        f"🧠 <b>Technologien:</b>\n{skills_text}\n\n"
        f"📅 <b>Erstellt:</b> {safe_created_at}\n"
        f"🔄 <b>Aktualisiert:</b> {safe_updated_at}"
    )


def send_project_card(chat_id, project):
    bot.send_message(
        chat_id,
        format_project(project),
        parse_mode="HTML",
        reply_markup=project_action_markup(project[0]),
        disable_web_page_preview=True,
    )


def no_projects(chat_id):
    bot.send_message(
        chat_id,
        "Du hast noch keine Portfolio-Projekte.\n"
        "Mit /new_project kannst du dein erstes Projekt hinzufügen."
    )


def cancel(message):
    bot.send_message(
        message.chat.id,
        "Aktion abgebrochen.",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@bot.message_handler(commands=["start"])
def start_command(message):
    bot.send_message(
        message.chat.id,
        "Hallo! 👋\n\n"
        "Ich bin dein Portfolio Bot. "
        "Ich helfe dir, Softwareprojekte, Technologien, "
        "Repository-Links und Projektstatus zu verwalten.\n\n"
        "Mit /help siehst du alle Funktionen."
    )


@bot.message_handler(commands=["help", "info"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "📌 *Portfolio Bot – Befehle*\n\n"
        "➕ /new_project – neues Projekt anlegen\n"
        "📂 /projects – Projekte anzeigen und filtern\n"
        "📊 /stats – Portfolio-Statistik\n"
        "🧠 /skills – Technologie zu einem Projekt hinzufügen\n"
        "➖ /remove_skill – Technologie entfernen\n"
        "✏️ /update_project – Projektdaten bearbeiten\n"
        "🗑 /delete_project – Projekt löschen\n\n"
        "Du kannst auch einfach den Namen eines Projekts senden, "
        "um die Projektkarte zu öffnen.",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["new_project"])
def new_project(message):
    bot.send_message(
        message.chat.id,
        "Wie heisst das neue Projekt?",
        reply_markup=cancel_markup(),
    )
    bot.register_next_step_handler(message, new_project_description)


def new_project_description(message):
    if message.text == CANCEL:
        cancel(message)
        return

    name = (message.text or "").strip()
    if not name:
        bot.send_message(
            message.chat.id,
            "Bitte gib einen Projektnamen ein.",
            reply_markup=cancel_markup(),
        )
        bot.register_next_step_handler(message, new_project_description)
        return

    if manager.project_exists(message.from_user.id, name):
        bot.send_message(
            message.chat.id,
            "Ein Projekt mit diesem Namen existiert bereits. "
            "Bitte gib einen anderen Namen ein.",
            reply_markup=cancel_markup(),
        )
        bot.register_next_step_handler(message, new_project_description)
        return

    data = {"name": name}
    bot.send_message(
        message.chat.id,
        "Bitte beschreibe das Projekt kurz:",
        reply_markup=cancel_markup(),
    )
    bot.register_next_step_handler(
        message,
        new_project_repository,
        data=data,
    )


def new_project_repository(message, data):
    if message.text == CANCEL:
        cancel(message)
        return

    data["description"] = (message.text or "").strip()

    bot.send_message(
        message.chat.id,
        "Bitte gib den Repository-Link ein:",
        reply_markup=cancel_markup(),
    )
    bot.register_next_step_handler(
        message,
        new_project_status,
        data=data,
    )


def new_project_status(message, data):
    if message.text == CANCEL:
        cancel(message)
        return

    data["url"] = (message.text or "").strip()
    statuses = [x[0] for x in manager.get_statuses()]

    bot.send_message(
        message.chat.id,
        "Bitte wähle den aktuellen Projektstatus:",
        reply_markup=reply_keyboard(statuses),
    )
    bot.register_next_step_handler(
        message,
        save_new_project,
        data=data,
        statuses=statuses,
    )


def save_new_project(message, data, statuses):
    if message.text == CANCEL:
        cancel(message)
        return

    status = message.text
    if status not in statuses:
        bot.send_message(
            message.chat.id,
            "Bitte wähle einen Status aus der Liste.",
            reply_markup=reply_keyboard(statuses),
        )
        bot.register_next_step_handler(
            message,
            save_new_project,
            data=data,
            statuses=statuses,
        )
        return

    project_id = manager.create_project(
        message.from_user.id,
        data["name"],
        data["description"],
        data["url"],
        status,
    )

    bot.send_message(
        message.chat.id,
        "✅ Projekt wurde gespeichert.",
        reply_markup=types.ReplyKeyboardRemove(),
    )

    project = manager.get_project(message.from_user.id, project_id)
    send_project_card(message.chat.id, project)


@bot.message_handler(commands=["projects"])
def projects_command(message):
    projects = manager.get_projects(message.from_user.id)

    if not projects:
        no_projects(message.chat.id)
        return

    bot.send_message(
        message.chat.id,
        "Welche Projekte möchtest du sehen?",
        reply_markup=project_filter_markup(),
    )


def show_projects(chat_id, user_id, status="Alle"):
    projects = manager.get_projects(user_id, status)

    if not projects:
        bot.send_message(
            chat_id,
            f"Keine Projekte mit dem Status „{status}“ gefunden."
        )
        return

    for project in projects:
        send_project_card(chat_id, project)


@bot.message_handler(commands=["stats"])
def stats_command(message):
    stats = manager.get_statistics(message.from_user.id)

    lines = [
        "📊 <b>Portfolio-Statistik</b>",
        "",
        f"Projekte insgesamt: <b>{stats['total']}</b>",
        "",
        "<b>Nach Status:</b>",
    ]

    for status, count in stats["by_status"]:
        lines.append(f"• {html.escape(str(status))}: {count}")

    lines.append("")
    lines.append("<b>Top-Technologien:</b>")

    if stats["top_skills"]:
        for skill, count in stats["top_skills"]:
            lines.append(f"• {html.escape(str(skill))}: {count}")
    else:
        lines.append("Noch keine Technologien hinzugefügt.")

    bot.send_message(
        message.chat.id,
        "\n".join(lines),
        parse_mode="HTML",
    )


def choose_project_for_action(message, action):
    projects = manager.get_projects(message.from_user.id)

    if not projects:
        no_projects(message.chat.id)
        return

    project_names = [project[1] for project in projects]

    prompts = {
        "add_skill": "Für welches Projekt möchtest du eine Technologie hinzufügen?",
        "remove_skill": "Von welchem Projekt möchtest du eine Technologie entfernen?",
        "update": "Welches Projekt möchtest du bearbeiten?",
        "delete": "Welches Projekt möchtest du löschen?",
    }

    bot.send_message(
        message.chat.id,
        prompts[action],
        reply_markup=reply_keyboard(project_names),
    )
    bot.register_next_step_handler(
        message,
        project_action_selected,
        action=action,
        project_names=project_names,
    )


@bot.message_handler(commands=["skills"])
def skills_command(message):
    choose_project_for_action(message, "add_skill")


@bot.message_handler(commands=["remove_skill"])
def remove_skill_command(message):
    choose_project_for_action(message, "remove_skill")


@bot.message_handler(commands=["update_project", "update_projects"])
def update_project_command(message):
    choose_project_for_action(message, "update")


@bot.message_handler(commands=["delete_project", "delete"])
def delete_project_command(message):
    choose_project_for_action(message, "delete")


def project_action_selected(message, action, project_names):
    if message.text == CANCEL:
        cancel(message)
        return

    project_name = message.text
    if project_name not in project_names:
        bot.send_message(
            message.chat.id,
            "Bitte wähle ein Projekt aus der Liste.",
            reply_markup=reply_keyboard(project_names),
        )
        bot.register_next_step_handler(
            message,
            project_action_selected,
            action=action,
            project_names=project_names,
        )
        return

    project = manager.get_project_by_name(
        message.from_user.id,
        project_name,
    )

    if action == "add_skill":
        start_add_skill(message, project[0])
    elif action == "remove_skill":
        start_remove_skill(message, project[0])
    elif action == "update":
        start_update_project(message, project[0])
    elif action == "delete":
        confirm_delete_project(message.chat.id, message.from_user.id, project[0])


def start_add_skill(message, project_id):
    skills = [x[1] for x in manager.get_skills()]

    bot.send_message(
        message.chat.id,
        "Wähle eine Technologie aus der Liste "
        "oder sende einen neuen Namen:",
        reply_markup=reply_keyboard(skills),
    )
    bot.register_next_step_handler(
        message,
        save_project_skill,
        project_id=project_id,
    )


def save_project_skill(message, project_id):
    if message.text == CANCEL:
        cancel(message)
        return

    skill = (message.text or "").strip()
    if not skill:
        bot.send_message(
            message.chat.id,
            "Bitte gib eine Technologie ein.",
            reply_markup=cancel_markup(),
        )
        bot.register_next_step_handler(
            message,
            save_project_skill,
            project_id=project_id,
        )
        return

    added = manager.add_project_skill(project_id, skill)

    if added:
        bot.send_message(
            message.chat.id,
            f"✅ {skill} wurde hinzugefügt.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
    else:
        bot.send_message(
            message.chat.id,
            f"ℹ️ {skill} ist bereits mit diesem Projekt verbunden.",
            reply_markup=types.ReplyKeyboardRemove(),
        )

    project = manager.get_project(message.from_user.id, project_id)
    if project:
        send_project_card(message.chat.id, project)


def start_remove_skill(message, project_id):
    skills = manager.get_project_skills(project_id)

    if not skills:
        bot.send_message(
            message.chat.id,
            "Dieses Projekt hat noch keine Technologien."
        )
        return

    bot.send_message(
        message.chat.id,
        "Welche Technologie möchtest du entfernen?",
        reply_markup=reply_keyboard(skills),
    )
    bot.register_next_step_handler(
        message,
        remove_project_skill,
        project_id=project_id,
        skills=skills,
    )


def remove_project_skill(message, project_id, skills):
    if message.text == CANCEL:
        cancel(message)
        return

    if message.text not in skills:
        bot.send_message(
            message.chat.id,
            "Bitte wähle eine Technologie aus der Liste.",
            reply_markup=reply_keyboard(skills),
        )
        bot.register_next_step_handler(
            message,
            remove_project_skill,
            project_id=project_id,
            skills=skills,
        )
        return

    manager.remove_project_skill(project_id, message.text)

    bot.send_message(
        message.chat.id,
        f"➖ {message.text} wurde entfernt.",
        reply_markup=types.ReplyKeyboardRemove(),
    )


def start_update_project(message, project_id):
    fields = list(UPDATE_FIELDS.keys())

    bot.send_message(
        message.chat.id,
        "Was möchtest du ändern?",
        reply_markup=reply_keyboard(fields),
    )
    bot.register_next_step_handler(
        message,
        update_field_selected,
        project_id=project_id,
        fields=fields,
    )


def update_field_selected(message, project_id, fields):
    if message.text == CANCEL:
        cancel(message)
        return

    if message.text not in fields:
        bot.send_message(
            message.chat.id,
            "Bitte wähle einen Eintrag aus der Liste.",
            reply_markup=reply_keyboard(fields),
        )
        bot.register_next_step_handler(
            message,
            update_field_selected,
            project_id=project_id,
            fields=fields,
        )
        return

    field, prompt = UPDATE_FIELDS[message.text]

    if field == "status_id":
        statuses = [x[0] for x in manager.get_statuses()]
        bot.send_message(
            message.chat.id,
            prompt,
            reply_markup=reply_keyboard(statuses),
        )
        bot.register_next_step_handler(
            message,
            save_project_update,
            project_id=project_id,
            field=field,
            allowed_values=statuses,
        )
    else:
        bot.send_message(
            message.chat.id,
            prompt,
            reply_markup=cancel_markup(),
        )
        bot.register_next_step_handler(
            message,
            save_project_update,
            project_id=project_id,
            field=field,
            allowed_values=None,
        )


def save_project_update(message, project_id, field, allowed_values):
    if message.text == CANCEL:
        cancel(message)
        return

    value = (message.text or "").strip()

    if allowed_values and value not in allowed_values:
        bot.send_message(
            message.chat.id,
            "Bitte wähle einen Wert aus der Liste.",
            reply_markup=reply_keyboard(allowed_values),
        )
        bot.register_next_step_handler(
            message,
            save_project_update,
            project_id=project_id,
            field=field,
            allowed_values=allowed_values,
        )
        return

    if field == "status_id":
        value = manager.get_status_id(value)

    if not value and field != "description":
        bot.send_message(
            message.chat.id,
            "Der Wert darf nicht leer sein.",
            reply_markup=(
                reply_keyboard(allowed_values)
                if allowed_values
                else cancel_markup()
            ),
        )
        bot.register_next_step_handler(
            message,
            save_project_update,
            project_id=project_id,
            field=field,
            allowed_values=allowed_values,
        )
        return

    updated = manager.update_project(
        message.from_user.id,
        project_id,
        field,
        value,
    )

    if not updated:
        bot.send_message(
            message.chat.id,
            "Die Änderung konnte nicht gespeichert werden. "
            "Möglicherweise existiert dieser Projektname bereits. "
            "Bitte versuche einen anderen Wert.",
            reply_markup=(
                reply_keyboard(allowed_values)
                if allowed_values
                else cancel_markup()
            ),
        )
        bot.register_next_step_handler(
            message,
            save_project_update,
            project_id=project_id,
            field=field,
            allowed_values=allowed_values,
        )
        return

    bot.send_message(
        message.chat.id,
        "✅ Projekt wurde aktualisiert.",
        reply_markup=types.ReplyKeyboardRemove(),
    )

    project = manager.get_project(message.from_user.id, project_id)
    if project:
        send_project_card(message.chat.id, project)


def confirm_delete_project(chat_id, user_id, project_id):
    project = manager.get_project(user_id, project_id)
    if not project:
        bot.send_message(chat_id, "Projekt nicht gefunden.")
        return

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "✅ Ja, löschen",
            callback_data=f"confirm_delete:{project_id}",
        ),
        InlineKeyboardButton(
            "Abbrechen",
            callback_data="cancel_delete",
        ),
    )

    bot.send_message(
        chat_id,
        f"Projekt „{project[1]}“ wirklich löschen?",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    user_id = call.from_user.id

    if data.startswith("filter:"):
        status = data.split(":", 1)[1]
        bot.answer_callback_query(call.id)
        show_projects(call.message.chat.id, user_id, status)
        return

    if data.startswith("edit:"):
        project_id = int(data.split(":", 1)[1])
        if not manager.get_project(user_id, project_id):
            bot.answer_callback_query(call.id, "Projekt nicht gefunden.")
            return
        bot.answer_callback_query(call.id)
        start_update_project(call.message, project_id)
        return

    if data.startswith("skills:"):
        project_id = int(data.split(":", 1)[1])
        if not manager.get_project(user_id, project_id):
            bot.answer_callback_query(call.id, "Projekt nicht gefunden.")
            return
        bot.answer_callback_query(call.id)
        start_add_skill(call.message, project_id)
        return

    if data.startswith("delete:"):
        project_id = int(data.split(":", 1)[1])
        bot.answer_callback_query(call.id)
        confirm_delete_project(call.message.chat.id, user_id, project_id)
        return

    if data.startswith("confirm_delete:"):
        project_id = int(data.split(":", 1)[1])
        project = manager.get_project(user_id, project_id)

        if project and manager.delete_project(user_id, project_id):
            bot.answer_callback_query(call.id, "Projekt gelöscht.")
            bot.send_message(
                call.message.chat.id,
                f"🗑 Projekt „{project[1]}“ wurde gelöscht."
            )
        return

    if data == "cancel_delete":
        bot.answer_callback_query(call.id, "Abgebrochen.")
        bot.send_message(call.message.chat.id, "Löschen abgebrochen.")


@bot.message_handler(func=lambda message: True)
def text_handler(message):
    project = manager.get_project_by_name(
        message.from_user.id,
        message.text or "",
    )

    if project:
        send_project_card(message.chat.id, project)
        return

    bot.reply_to(
        message,
        "Projekt nicht gefunden. Mit /help siehst du alle Befehle."
    )


if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
