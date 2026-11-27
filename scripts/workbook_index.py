"""Index conventions shared by the workbook's build scripts."""
import re


GUIDE = "20261125T012000--grh-workbook__guide.org"

OVERVIEW_LINK = re.compile(
    r"^\[\[file:(?P<id>\d{8}T\d{6})--(?P<slug>[^/\]]+)__workbook\.html\]\[Overview\]\]",
    re.M,
)


def overview_sheet(guide):
    """Read the optional sheet from the navigation line above Part I."""
    match = OVERVIEW_LINK.search(guide)
    return (match["id"], match["slug"]) if match else None
