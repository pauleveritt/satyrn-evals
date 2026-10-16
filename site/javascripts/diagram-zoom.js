// Click a diagram, or focus it and press Enter, to see it enlarged over the
// page; click anywhere or press Esc to close. The diagram is enlarged in place: its drawing lives in a
// closed shadow root, so it cannot be copied into a separate dialog.
(() => {
  let open = null;

  function close() {
    if (!open) {
      return;
    }
    open.diagram.classList.remove("diagram-zoomed");
    open.placeholder.remove();
    open.backdrop.remove();
    open = null;
  }

  function enlarge(diagram) {
    // Keep the page from jumping while the diagram is out of the flow.
    const placeholder = document.createElement("div");
    placeholder.style.height = `${diagram.offsetHeight}px`;
    diagram.before(placeholder);
    const backdrop = document.createElement("div");
    backdrop.className = "diagram-backdrop";
    document.body.append(backdrop);
    diagram.classList.add("diagram-zoomed");
    open = { diagram, placeholder, backdrop };
  }

  function diagramOf(target) {
    return target && target.closest ? target.closest("div.mermaid") : null;
  }

  document.addEventListener("click", (event) => {
    if (open) {
      close();
      return;
    }
    const diagram = diagramOf(event.target);
    if (diagram) {
      enlarge(diagram);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      close();
    } else if (event.key === "Enter" && !open) {
      const diagram = diagramOf(document.activeElement);
      if (diagram) {
        event.preventDefault();
        enlarge(diagram);
      }
    }
  });

  // Diagrams are rendered after the page loads; make each one reachable by Tab.
  function focusable(root) {
    for (const diagram of root.querySelectorAll("div.mermaid")) {
      diagram.tabIndex = 0;
    }
  }
  focusable(document);
  new MutationObserver(() => focusable(document)).observe(document.body, { childList: true, subtree: true });
})();
