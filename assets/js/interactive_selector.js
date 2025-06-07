// Interactive Element Selector for Web Scraping - Simplified Version
// This script creates an overlay that allows users to click on elements to generate CSS selectors

(function() {
  'use strict';
  
  // Avoid double-injection
  if (document.getElementById('scrapeOverlay')) {
    const titleDiv = document.getElementById('scrapeOverlayTitle');
    if (titleDiv && window.scraperContextMessage) {
      titleDiv.textContent = window.scraperContextMessage;
      delete window.scraperContextMessage;
    }
    return;
  }

  // State
  let isActive = true;
  let hoveredElement = null;
  let selectedElement = null;

  // ======== Helper: Generate CSS selector ========
  function getCssSelector(el) {
    if (!(el instanceof Element)) return null;

    // If element has a good ID, use it
    if (el.id && /^[a-zA-Z][\w-]*$/.test(el.id)) {
      return `#${CSS.escape(el.id)}`;
    }

    // Build path
    const path = [];
    let current = el;
    
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      
      // Add class if unique among siblings
      if (current.className) {
        const classes = Array.from(current.classList)
          .filter(c => c && !c.includes('scraper-highlight'))
          .map(c => `.${CSS.escape(c)}`)
          .join('');
        if (classes) {
          selector += classes;
        }
      }
      
      // Add nth-child if needed for uniqueness
      if (current.parentElement) {
        const siblings = Array.from(current.parentElement.children);
        const sameTagSiblings = siblings.filter(s => 
          s.tagName === current.tagName && 
          s.className === current.className
        );
        
        if (sameTagSiblings.length > 1) {
          const index = sameTagSiblings.indexOf(current) + 1;
          selector += `:nth-of-type(${index})`;
        }
      }
      
      path.unshift(selector);
      current = current.parentElement;
    }
    
    return path.join(' > ');
  }

  // ======== Create UI Elements ========
  
  // Overlay (visual only, no interaction)
  const overlay = document.createElement('div');
  overlay.id = 'scrapeOverlay';
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.2);
    z-index: 2147483645;
    pointer-events: none;
  `;

  // Info Panel
  const infoPanel = document.createElement('div');
  infoPanel.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: white;
    border: 2px solid #2196F3;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    z-index: 2147483646;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    min-width: 400px;
    max-width: 600px;
  `;

  infoPanel.innerHTML = `
    <h3 style="margin: 0 0 10px 0; color: #333; font-size: 18px;">
      ${window.scraperContextMessage || 'Click on an element to select it'}
    </h3>
    <p style="margin: 0 0 15px 0; color: #666;">
      Move your mouse over elements to highlight them. Click to select.
    </p>
    <div style="display: flex; gap: 10px; justify-content: center;">
      <button id="scraper-done-btn" style="
        background: #4CAF50;
        color: white;
        border: none;
        padding: 8px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
      ">Done</button>
      <button id="scraper-cancel-btn" style="
        background: #f44336;
        color: white;
        border: none;
        padding: 8px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
      ">Cancel</button>
    </div>
    <div id="scraper-selection-info" style="margin-top: 15px; display: none;">
      <div style="background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px;">
        <div id="scraper-selector-text"></div>
      </div>
    </div>
  `;

  // ======== Event Handlers ========
  
  function highlightElement(element) {
    if (!element || element === hoveredElement) return;
    
    // Remove previous highlight
    if (hoveredElement) {
      hoveredElement.classList.remove('scraper-highlight-hover');
    }
    
    // Add new highlight
    hoveredElement = element;
    hoveredElement.classList.add('scraper-highlight-hover');
  }

  function selectElement(element) {
    if (!element || !isActive) return;
    
    // Store selection data
    const selector = getCssSelector(element);
    const text = element.textContent.trim().substring(0, 100);
    
    const data = {
      selector: selector,
      text: text,
      tagName: element.tagName.toLowerCase(),
      classes: Array.from(element.classList).filter(c => !c.includes('scraper-'))
    };
    
    // Update or create hidden input
    let input = document.getElementById('selected_element_data');
    if (!input) {
      input = document.createElement('input');
      input.type = 'hidden';
      input.id = 'selected_element_data';
      document.body.appendChild(input);
    }
    input.value = JSON.stringify(data);
    
    // Visual feedback
    if (selectedElement) {
      selectedElement.classList.remove('scraper-highlight-selected');
    }
    selectedElement = element;
    selectedElement.classList.add('scraper-highlight-selected');
    
    // Update info panel
    const infoDiv = document.getElementById('scraper-selection-info');
    const selectorText = document.getElementById('scraper-selector-text');
    infoDiv.style.display = 'block';
    selectorText.textContent = `Selected: ${selector}`;
    
    // Auto close after 2 seconds
    setTimeout(cleanup, 2000);
  }

  function handleMouseMove(e) {
    if (!isActive) return;
    
    const element = document.elementFromPoint(e.clientX, e.clientY);
    if (element && !infoPanel.contains(element)) {
      highlightElement(element);
    }
  }

  function handleClick(e) {
    if (!isActive) return;
    
    const element = e.target;
    
    // Ignore clicks on our UI
    if (infoPanel.contains(element)) {
      return;
    }
    
    // Prevent the click from doing anything else
    e.preventDefault();
    e.stopPropagation();
    
    selectElement(element);
  }

  function handleKeyPress(e) {
    if (e.key === 'Escape') {
      cleanup();
    }
  }

  function cleanup() {
    isActive = false;
    
    // Remove highlights
    document.querySelectorAll('.scraper-highlight-hover, .scraper-highlight-selected').forEach(el => {
      el.classList.remove('scraper-highlight-hover', 'scraper-highlight-selected');
    });
    
    // Remove elements
    overlay.remove();
    infoPanel.remove();
    
    // Remove styles
    const styleElement = document.getElementById('scraper-styles');
    if (styleElement) styleElement.remove();
    
    // Remove event listeners
    document.removeEventListener('mousemove', handleMouseMove, true);
    document.removeEventListener('click', handleClick, true);
    document.removeEventListener('keydown', handleKeyPress, true);
  }

  // ======== Setup ========
  
  // Add styles
  const styles = document.createElement('style');
  styles.id = 'scraper-styles';
  styles.textContent = `
    .scraper-highlight-hover {
      outline: 2px solid #2196F3 !important;
      outline-offset: 2px !important;
      cursor: pointer !important;
    }
    .scraper-highlight-selected {
      outline: 3px solid #4CAF50 !important;
      outline-offset: 2px !important;
      background-color: rgba(76, 175, 80, 0.1) !important;
    }
  `;
  document.head.appendChild(styles);

  // Add elements to page
  document.body.appendChild(overlay);
  document.body.appendChild(infoPanel);

  // Attach event listeners
  document.addEventListener('mousemove', handleMouseMove, true);
  document.addEventListener('click', handleClick, true);
  document.addEventListener('keydown', handleKeyPress, true);

  // Button handlers
  document.getElementById('scraper-done-btn').onclick = function() {
    if (!document.getElementById('selected_element_data')) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.id = 'selected_element_data';
      input.value = 'DONE_SELECTING';
      document.body.appendChild(input);
    }
    cleanup();
  };

  document.getElementById('scraper-cancel-btn').onclick = cleanup;

  // Clean up context message
  delete window.scraperContextMessage;

})();