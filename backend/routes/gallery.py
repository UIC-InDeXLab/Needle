from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core import query_manager
from core.query import Query

router = APIRouter()

# We assume templates are defined in main.py as templates = Jinja2Templates(directory="templates")
# Since we are not creating a global templates object here, we'll import from main if needed.
# However, typically you would pass or re-import Jinja2Templates.
# For simplicity, let's just re-initialize here, but ideally, you'd share this from main.
templates = Jinja2Templates(directory="templates")


@router.get("/gallery/{qid}", response_class=HTMLResponse)
async def gallery(request: Request, qid: int, page: int = 1):
    # Validate query and retrieve results
    query_object: Query = query_manager.get_query(qid)
    if query_object is None:
        raise HTTPException(status_code=404, detail="Query not found")

    results = query_object.final_results
    if results is None:
        # Maybe the query hasn't been searched yet?
        results = []

    # Pagination
    page_size = 16
    start = (page - 1) * page_size
    end = start + page_size
    paginated_results = results[start:end]

    # Determine pagination controls
    has_next = len(results) > end
    has_prev = page > 1

    # Render template
    return templates.TemplateResponse("gallery.html", {
        "request": request,
        "query": query_object.query,
        "results": paginated_results,
        "page": page,
        "has_next": has_next,
        "has_prev": has_prev,
        "qid": qid
    })
