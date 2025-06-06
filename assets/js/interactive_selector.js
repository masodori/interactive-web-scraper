// interactive_scraper_js.js
// Enhanced overlay with hover‐highlighting for container identification and robust CSS selector generation.

(function() {
  // Avoid double‐injection
  if (document.getElementById('scrapeOverlay')) {
    // Update context message if overlay already exists
    const titleDiv = document.getElementById('scrapeOverlayTitle');
    if (titleDiv && window.scraperContextMessage) {
      titleDiv.textContent = window.scraperContextMessage;
      delete window.scraperContextMessage;
    }
    return;
  }

  // ======== Helper: Generate a unique CSS selector for a given element ========
  function getCssSelector(el) {
    if (!(el instanceof Element)) return null;

    // If element has ID, return '#id'
    if (el.id) {
      return `#${CSS.escape(el.id)}`;
    }

    // Build the path segments array
    const segments = [];
    let current = el;
    while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body) {
      let segment = current.tagName.toLowerCase();

      // If element has classes, try to pick a unique class among siblings
      const classList = Array.from(current.classList).filter(c => c.trim().length > 0);
      if (classList.length) {
        // Try each class to see if it's unique among siblings
        for (const cls of classList) {
          const sameClassSiblings = Array.from(current.parentNode.children).filter(
            sib => sib !== current && sib.classList.contains(cls)
          );
          if (sameClassSiblings.length === 0) {
            segment += `.${CSS.escape(cls)}`;
            break;
          }
        }
      }

      // If no unique class chosen or no classes at all, fallback to nth‐of‐type
      if (!segment.includes('.')) {
        const nth = Array.prototype.indexOf.call(
          current.parentNode.children,
          current
        ) + 1;
        segment += `:nth‐of‐type(${nth})`;
      }

      segments.unshift(segment);
      current = current.parentNode;
    }

    // If no segments collected, return element tag
    if (segments.length === 0) {
      return el.tagName.toLowerCase();
    }

    return segments.join(' > ');
  }

  // ======== Create and insert hidden input for communication ========
  let hiddenInput = document.getElementById('selected_element_data');
  if (!hiddenInput) {
    hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.id = 'selected_element_data';
    hiddenInput.value = '';
    document.body.appendChild(hiddenInput);
  } else {
    hiddenInput.value = '';
  }

  // ======== Create overlay container ========
  const overlay = document.createElement('div');
  overlay.id = 'scrapeOverlay';
  Object.assign(overlay.style, {
    position: 'fixed',
    top: '10px',
    right: '10px',
    width: '300px',
    maxHeight: '80vh',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    border: '2px solid #333',
    borderRadius: '8px',
    zIndex: '999999',
    boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
    padding: '10px',
    overflowY: 'auto',
    fontFamily: 'Arial, sans-serif',
    fontSize: '14px',
    color: '#222'
  });

  // ======== Title / Context Message ========
  const titleDiv = document.createElement('div');
  titleDiv.id = 'scrapeOverlayTitle';
  titleDiv.textContent = window.scraperContextMessage || 'Select elements';
  Object.assign(titleDiv.style, {
    fontWeight: 'bold',
    marginBottom: '8px'
  });
  overlay.appendChild(titleDiv);
  delete window.scraperContextMessage;

  // ======== Instruction Text ========
  const instr = document.createElement('div');
  instr.textContent = 'Hover to highlight, click to capture selector.';
  Object.assign(instr.style, {
    marginBottom: '8px'
  });
  overlay.appendChild(instr);

  // ======== Selected Element Info ========
  const selectedInfo = document.createElement('div');
  selectedInfo.id = 'selectedInfo';
  selectedInfo.textContent = 'No element selected yet.';
  Object.assign(selectedInfo.style, {
    fontStyle: 'italic',
    marginBottom: '8px',
    whiteSpace: 'pre-wrap'
  });
  overlay.appendChild(selectedInfo);

  // ======== Done Selecting Button ========
  const doneBtn = document.createElement('button');
  doneBtn.id = 'scrapeDoneBtn';
  doneBtn.textContent = 'Done Selecting';
  Object.assign(doneBtn.style, {
    display: 'block',
    width: '100%',
    padding: '6px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: '#4CAF50',
    color: 'white',
    fontSize: '14px',
    cursor: 'pointer'
  });
  doneBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    hiddenInput.value = 'DONE_SELECTING';
    removeOverlayAndListeners();
  });
  overlay.appendChild(doneBtn);

  document.body.appendChild(overlay);

  // ======== Variables for Hover Highlighting ========
  let lastHovered = null;

  // ======== Hover Event Handlers ========
  function onMouseOver(e) {
    const t = e.target;
    // Ignore overlay and hidden input
    if (overlay.contains(t) || t.id === 'selected_element_data') return;
    // Remove outline from previous
    if (lastHovered && lastHovered !== t) {
      lastHovered.style.outline = '';
    }
    // Add dashed blue outline
    t.style.outline = '2px dashed #2196F3';
    lastHovered = t;
  }

  function onMouseOut(e) {
    const t = e.target;
    if (overlay.contains(t) || t.id === 'selected_element_data') return;
    if (lastHovered === t) {
      t.style.outline = '';
      lastHovered = null;
    }
  }

  // ======== Click Event Handler (capturing phase) ========
  function onClickCapture(event) {
    // If click is inside overlay, ignore
    if (overlay.contains(event.target)) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    const clicked = event.target;
    const selector = getCssSelector(clicked) || '';
    const text = clicked.innerText.trim().slice(0, 300); // limit length

    // Visual feedback: temporary solid outline
    clicked.style.outline = '3px solid #FF5722';
    setTimeout(() => {
      // Only clear if it's still the forced outline
      if (clicked.style.outline === '3px solid #FF5722') {
        clicked.style.outline = '';
      }
    }, 1000);

    // Update overlay info
    selectedInfo.textContent = `Selector:\n${selector}\n\nText:\n${text || '[no text]'}`;

    // Send data back to Python via hidden input
    const payload = {
      type: 'element_selected',
      selector: selector,
      text: text
    };
    hiddenInput.value = JSON.stringify(payload);
  }

  // ======== Remove overlay and all event listeners ========
  function removeOverlayAndListeners() {
    document.removeEventListener('click', onClickCapture, true);
    document.removeEventListener('mouseover', onMouseOver, true);
    document.removeEventListener('mouseout', onMouseOut, true);
    const existingOverlay = document.getElementById('scrapeOverlay');
    if (existingOverlay) {
      existingOverlay.remove();
    }
    // Clear any lingering highlight
    if (lastHovered) {
      lastHovered.style.outline = '';
      lastHovered = null;
    }
  }

  // ======== Attach event listeners in capturing phase ========
  document.addEventListener('click', onClickCapture, true);
  document.addEventListener('mouseover', onMouseOver, true);
  document.addEventListener('mouseout', onMouseOut, true);
})();