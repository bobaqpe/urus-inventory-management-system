const BUSINESS_KEY = 'urus-business-id';

/** Adds a compact, keyboard accessible business picker beside the page title. */
export function renderBusinessSwitcher(heading, businesses, selectedId, onSelect) {
  if (!heading || !Array.isArray(businesses) || businesses.length < 2) return null;

  const host = document.createElement('div');
  host.className = 'business-switcher';
  host.innerHTML = '<button class="business-switcher-toggle" type="button" aria-label="Switch business" aria-haspopup="true" aria-expanded="false"><span class="business-switcher-chevron" aria-hidden="true"></span></button><div class="business-switcher-menu" role="menu" hidden></div>';
  heading.parentNode.insertBefore(host, heading);
  host.append(heading);

  const toggle = host.querySelector('.business-switcher-toggle');
  const menu = host.querySelector('.business-switcher-menu');
  const close = () => { menu.hidden = true; toggle.setAttribute('aria-expanded', 'false'); };
  const open = () => { menu.hidden = false; toggle.setAttribute('aria-expanded', 'true'); };
  toggle.addEventListener('click', () => menu.hidden ? open() : close());
  const options = new Map();
  businesses.forEach(business => {
    const option = document.createElement('button');
    option.type = 'button';
    option.className = 'business-switcher-option';
    option.setAttribute('role', 'menuitem');
    option.textContent = business.name;
    if (String(business.id) === String(selectedId)) {
      option.classList.add('is-current');
      option.setAttribute('aria-current', 'true');
    }
    option.addEventListener('click', () => {
      options.forEach(entry => {
        const current = entry === option;
        entry.classList.toggle('is-current', current);
        if (current) entry.setAttribute('aria-current', 'true');
        else entry.removeAttribute('aria-current');
      });
      sessionStorage.setItem(BUSINESS_KEY, String(business.id));
      close();
      onSelect?.(business);
    });
    options.set(business.id, option);
    menu.append(option);
  });
  document.addEventListener('click', event => { if (!host.contains(event.target)) close(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
  return host;
}
