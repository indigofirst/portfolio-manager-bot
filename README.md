# Portfolio Manager Bot

Ein Telegram-Bot zur Verwaltung eigener Softwareprojekte mit Beschreibung, Repository-Link, Status und verwendeten Technologien.

## Funktionen

- neue Projekte anlegen, anzeigen, bearbeiten und löschen
- Projekte nach Status filtern
- Technologien zu Projekten hinzufügen und entfernen
- Schutz vor doppelten Projektnamen pro Benutzer
- Portfolio-Statistik und häufig verwendete Technologien
- getrennte Portfolios für verschiedene Telegram-Benutzer

## Technologien

- Python 3.10+
- pyTelegramBotAPI
- SQLite / SQL
- relationale Datenbanken
- Foreign Keys und Many-to-Many-Beziehungen

## Projektstruktur

```text
portfolio-manager-bot/
├── .gitignore
├── config.py
├── logic.py
├── main.py
├── README.md
└── requirements.txt
```

`portfolio.db` wird beim ersten Start automatisch erstellt.

## Installation

```bash
pip install -r requirements.txt
```

Telegram-Bot über BotFather erstellen und den Token in `config.py` eintragen:

```python
TOKEN = "DEIN_BOT_TOKEN"
```

Bot starten:

```bash
python main.py
```

## Befehle

- `/start` – Bot starten
- `/help` – Befehle anzeigen
- `/new_project` – neues Projekt anlegen
- `/projects` – Projekte anzeigen und filtern
- `/stats` – Portfolio-Statistik anzeigen
- `/skills` – Technologie hinzufügen
- `/remove_skill` – Technologie entfernen
- `/update_project` – Projektdaten bearbeiten
- `/delete_project` – Projekt löschen

Ein Projekt kann zusätzlich durch Senden seines Namens direkt geöffnet werden.

## Technische Details

- Projekte, Status und Technologien werden relational in SQLite gespeichert.
- `project_skills` bildet die Many-to-Many-Beziehung zwischen Projekten und Technologien ab.
- Foreign Keys mit `ON DELETE CASCADE` bereinigen Projekt-Technologie-Zuordnungen automatisch.
- Benutzereingaben in Projektkarten werden für die Telegram-Ausgabe maskiert.
- Inline-Aktionen prüfen den Besitzer des Projekts über die Telegram-`user_id`.

## Einschränkungen

- Die Datenbank ist lokal und nicht zwischen mehreren Bot-Instanzen synchronisiert.
- Das Projekt enthält keine Benutzeranmeldung ausserhalb der Telegram-`user_id`.

## Sicherheit

Ein echter Telegram-Bot-Token gehört nicht in ein öffentliches Repository. Vor dem Hochladen sollte `TOKEN` in `config.py` leer sein oder einen Platzhalter enthalten.
