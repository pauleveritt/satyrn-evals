// Click a diagram to see it enlarged over the page; click anywhere or press
// Esc to close. The diagram is enlarged in place: its drawing lives in a
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

  document.addEventListener("click", (event) => {
    if (open) {
      close();
      return;
    }
    const diagram = event.target.closest && event.target.closest("div.mermaid");
    if (!diagram) {
      return;
    }
    // Keep the page from jumping while the diagram is out of the flow.
    const placeholder = document.createElement("div");
    placeholder.style.height = `${diagram.offsetHeight}px`;
    diagram.before(placeholder);
    const backdrop = document.createElement("div");
    backdrop.className = "diagram-backdrop";
    document.body.append(backdrop);
    diagram.classList.add("diagram-zoomed");
    open = { diagram, placeholder, backdrop };
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      close();
    }
  });
})();
