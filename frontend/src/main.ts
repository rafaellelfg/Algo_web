import "./style.css";
import { auth } from "./auth";
import { showGraphs } from "./graph";
import { showHistory } from "./history";
import { initVisualizer } from "./visualizer";

const views = {
  main: document.querySelector<HTMLElement>("#view-main")!,
  graphs: document.querySelector<HTMLElement>("#view-graphs")!,
  practice: document.querySelector<HTMLElement>("#view-practice")!,
  history: document.querySelector<HTMLElement>("#view-history")!,
};
type Route = keyof typeof views;

function currentRoute(): Route {
  const hash = location.hash.replace(/^#\/?/, "").split("/")[0];
  return hash in views && hash !== "main" ? (hash as Route) : "main";
}

/** Tiny hash router: #/ = trees, #/graphs, #/practice, #/history */
function route(): void {
  const r = currentRoute();
  for (const [name, el] of Object.entries(views)) el.hidden = name !== r;
  document.querySelectorAll<HTMLAnchorElement>("[data-route]").forEach((a) => {
    a.classList.toggle("active", a.dataset.route === r);
  });
  if (r === "history") void showHistory();
  if (r === "graphs") showGraphs();
}

window.addEventListener("hashchange", route);
auth.onChange(() => {
  if (currentRoute() === "history") void showHistory();
});

// Find out who is logged in first (this also sets the CSRF cookie), then start.
void auth.init().then(() => {
  initVisualizer();
  route();
});
