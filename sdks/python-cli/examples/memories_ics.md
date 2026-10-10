# Put your memories and learnings on a calendar (.ics)

Use this recipe to see when Omi captured memories, facts, and learnings on your
calendar, alongside your daily schedule and meetings. It reads a saved JSON
export, makes no network requests, and generates an RFC 5545 iCalendar file
supported by Google Calendar, Apple Calendar, Outlook, and Thunderbird.

Export up to 200 memories:

```sh
omi --json memory list --limit 200 --offset 0 > memories.json
```

Check that the command succeeded before converting the file.

Convert to an iCalendar file:

```sh
python memories_to_ics.py memories.ics memories.json
```

You can pass multiple JSON export files in one command to merge pages. Duplicates
with identical IDs are automatically deduplicated.

## Importing into calendars

- **Google Calendar**: Go to Settings → Import & Export → Import, select `memories.ics`.
- **Apple Calendar**: File → Import, choose `memories.ics`.
- **Outlook**: Add Calendar → Upload from file.
