// Interactive Element Selector for Web Scraping
// This script creates an overlay that allows users to click on elements to generate CSS selectors

(function() {
  // Avoid double-injection
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
    if (el.id && /^[a-zA-Z][\w-]*$/.test(el.id)) {
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
          if (!current.parentNode) break;
          const sameClassSiblings = Array.from(current.parentNode.children).filter(
            sib => sib !== current && sib.classList.contains(cls)
          );
          if (sameClassSiblings.length === 0) {
            segment += `.${CSS.escape(cls)}`;
            break;
          }
        }
      }

      // If no unique class chosen or no classes at all, use nth-of-type
      if (!segment.includes('.')) {
        const nth = Array.prototype.indexOf.call(
          current.parentNode.children,
          current
        ) + 1;
        if (nth > 1) {
          segment += `:nth-of-type(${nth})`;
        }
      }

      segments.unshift(segment);
      current = current.parentNode;
    }

    return segments.join(' > ');
  }

  // ======== Helper: Get element's text content (trimmed) ========
  function getElementText(el) {
    return el.textContent.trim().substring(0, 100);
  }

  // ======== Create Overlay ========
  const overlay = document.createElement('div');
  overlay.id = 'scrapeOverlay';
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.3);
    z-index: 999999;
    cursor: crosshair;
  `;

  // ======== Create Info Box ========
  const infoBox = document.createElement('div');
  infoBox.style.cssText = `
    position: fixed;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    background: white;
    padding: 15px 25px;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    z-index: 1000000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    min-width: 300px;
    text-align: center;
  `;

  // Add title
  const title = document.createElement('div');
  title.id = 'scrapeOverlayTitle';
  title.style.cssText = `
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 10px;
    color: #333;
  `;
  title.textContent = window.scraperContextMessage || 'Click on an element to select it';
  delete window.scraperContextMessage;
  infoBox.appendChild(title);

  // Add instructions
  const instructions = document.createElement('div');
  instructions.style.cssText = `
    font-size: 14px;
    color: #666;
    margin-bottom: 15px;
  `;
  instructions.textContent = 'Hover to highlight • Click to select • ESC to cancel';
  infoBox.appendChild(instructions);

  // Add done button
  const doneBtn = document.createElement('button');
  doneBtn.style.cssText = `
    background: #4CAF50;
    color: white;
    border: none;
    padding: 8px 20px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    margin-right: 10px;
  `;
  doneBtn.textContent = 'Done Selecting';
  doneBtn.onclick = function() {
    // Signal that we're done
    if (!document.getElementById('selected_element_data')) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.id = 'selected_element_data';
      input.value = 'DONE_SELECTING';
      document.body.appendChild(input);
    } else {
      document.getElementById('selected_element_data').value = 'DONE_SELECTING';
    }
    cleanup();
  };
  infoBox.appendChild(doneBtn);

  // Add cancel button
  const cancelBtn = document.createElement('button');
  cancelBtn.style.cssText = `
    background: #f44336;
    color: white;
    border: none;
    padding: 8px 20px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
  `;
  cancelBtn.textContent = 'Cancel';
  cancelBtn.onclick = cleanup;
  infoBox.appendChild(cancelBtn);

  // ======== Hover Effect ========
  let hoveredElement = null;

  function handleMouseMove(e) {
    // Remove previous highlight
    if (hoveredElement) {
      hoveredElement.style.outline = '';
    }

    // Find element under cursor (excluding our overlay)
    const element = document.elementFromPoint(e.clientX, e.clientY);
    
    if (element && element !== overlay && element !== infoBox && !infoBox.contains(element)) {
      hoveredElement = element;
      hoveredElement.style.outline = '3px solid #2196F3';
    }
  }

  // ======== Click Handler ========
  function handleClick(e) {
    e.preventDefault();
    e.stopPropagation();

    const element = document.elementFromPoint(e.clientX, e.clientY);
    
    if (element && element !== overlay && element !== infoBox && !infoBox.contains(element)) {
      const selector = getCssSelector(element);
      const text = getElementText(element);
      
      // Store the selected element data
      const data = {
        selector: selector,
        text: text,
        tagName: element.tagName.toLowerCase(),
        classes: Array.from(element.classList)
      };

      // Create or update hidden input with selection data
      let input = document.getElementById('selected_element_data');
      if (!input) {
        input = document.createElement('input');
        input.type = 'hidden';
        input.id = 'selected_element_data';
        document.body.appendChild(input);
      }
      input.value = JSON.stringify(data);

      // Visual feedback
      element.style.outline = '3px solid #4CAF50';
      
      // Update info box
      title.textContent = 'Element Selected!';
      instructions.innerHTML = `<strong>Selector:</strong> ${selector}<br><strong>Text:</strong> ${text.substring(0, 50)}${text.length > 50 ? '...' : ''}`;
      
      // Auto-close after a short delay
      setTimeout(cleanup, 1500);
    }
  }

  // ======== Cleanup Function ========
  function cleanup() {
    overlay.remove();
    infoBox.remove();
    if (hoveredElement) {
      hoveredElement.style.outline = '';
    }
    document.removeEventListener('keydown', handleEscape);
  }

  // ======== ESC Key Handler ========
  function handleEscape(e) {
    if (e.key === 'Escape') {
      cleanup();
    }
  }

  // ======== Attach Event Listeners ========
  overlay.addEventListener('mousemove', handleMouseMove);
  overlay.addEventListener('click', handleClick);
  document.addEventListener('keydown', handleEscape);

  // ======== Add to Page ========
  document.body.appendChild(overlay);
  document.body.appendChild(infoBox);

  // Hide overlay temporarily to allow interaction with elements underneath
  overlay.style.pointerEvents = 'none';
  
  // Re-enable pointer events on mouse move
  document.addEventListener('mousemove', function enablePointer(e) {
    overlay.style.pointerEvents = 'auto';
    document.removeEventListener('mousemove', enablePointer);
  });

})();