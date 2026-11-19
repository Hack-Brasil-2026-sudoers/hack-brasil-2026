const directions = document.querySelector('#directions');
const displayMode = document.querySelector('#display-mode');

if (new URLSearchParams(location.search).get('view') === 'compare') {
  displayMode.value = 'compare';
  directions.classList.add('compare');
}

displayMode.addEventListener('change', () => {
  directions.classList.toggle('compare', displayMode.value === 'compare');
});

document.querySelectorAll('[data-example]').forEach(button => {
  const example = document.getElementById(`${button.dataset.example}-correction`);
  const originalLabel = button.textContent;
  button.setAttribute('aria-expanded', 'false');
  button.setAttribute('aria-controls', example.id);
  button.addEventListener('click', () => {
    const isExpanded = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', String(!isExpanded));
    button.textContent = isExpanded ? originalLabel : 'Hide correction';
    example.hidden = isExpanded;
  });
});
