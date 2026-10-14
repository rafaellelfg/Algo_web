import "./style.css";
import { showAdmin } from "./admin";
import { auth } from "./auth";
import "./keys"; // the "API key" window
import { showGraphs } from "./graph";
import { showHistory } from "./history";
import { initVisualizer } from "./visualizer";

const views = {
  main: document.querySelector<HTMLElement>("#view-main")!,
  graphs: document.querySelector<HTMLElement>("#view-graphs")!,
  practice: document.querySelector<HTMLElement>("#view-practice")!,
  history: document.querySelector<HTMLElement>("#view-history")!,
  admin: document.querySelector<HTMLElement>("#view-admin")!,
};
type Route = keyof typeof views;

function currentRoute(): Route {
  const hash = location.hash.replace(/^#\/?/, "").split("/")[0];
  return hash in views && hash !== "main" ? (hash as Route) : "main";
}

/** Tiny hash router: #/ = trees, #/graphs, #/practice, #/history, #/admin */
function route(): void {
  const r = currentRoute();
  document.dispatchEvent(new CustomEvent("route-change"));
  for (const [name, el] of Object.entries(views)) el.hidden = name !== r;
  document.querySelectorAll<HTMLAnchorElement>("[data-route]").forEach((a) => {
    a.classList.toggle("active", a.dataset.route === r);
  });
  if (r === "history") void showHistory();
  if (r === "graphs") showGraphs();
  if (r === "admin") void showAdmin();
}

window.addEventListener("hashchange", route);
auth.onChange(() => {
  document.querySelector<HTMLElement>("#admin-tab")!.hidden = !auth.isAdmin;
  if (currentRoute() === "history") void showHistory();
  if (currentRoute() === "admin") void showAdmin();
});

// Check the stored API key first (is it still valid?), then start.
void auth.init().then(() => {
  initVisualizer();
  route();
});
