document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("select[data-searchable='true']").forEach(enhanceSelect);
});

function enhanceSelect(select) {
    const options = Array.from(select.options).filter((option) => option.value);
    const wrapper = document.createElement("div");
    wrapper.className = "search-select";

    const control = document.createElement("div");
    control.className = "search-select__control";

    const input = document.createElement("input");
    input.type = "search";
    input.className = "search-select__input";
    input.placeholder = select.dataset.placeholder || "Search…";
    input.autocomplete = "off";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");

    const menu = document.createElement("div");
    menu.className = "search-select__menu";
    menu.setAttribute("role", "listbox");
    menu.hidden = true;

    const wasRequired = select.required;
    select.required = false;
    input.required = wasRequired;
    select.classList.add("search-select__native");
    select.parentNode.insertBefore(wrapper, select);
    control.appendChild(input);
    wrapper.appendChild(control);
    wrapper.appendChild(menu);
    wrapper.appendChild(select);

    let visibleOptions = [];
    let activeIndex = -1;

    function choose(option) {
        select.value = option.value;
        input.value = option.text.trim();
        input.setCustomValidity("");
        select.dispatchEvent(new Event("change", { bubbles: true }));
        closeMenu();
    }

    function render(query = "") {
        const normalized = query.trim().toLowerCase();
        visibleOptions = options.filter((option) =>
            option.text.toLowerCase().includes(normalized)
        );
        activeIndex = -1;
        menu.replaceChildren();

        if (!visibleOptions.length) {
            const empty = document.createElement("div");
            empty.className = "search-select__empty";
            empty.textContent = select.dataset.emptyMessage || "No matching options";
            menu.appendChild(empty);
            return;
        }

        visibleOptions.forEach((option) => {
            const item = document.createElement("div");
            item.className = "search-select__option";
            item.setAttribute("role", "option");
            item.textContent = option.text.trim();
            item.addEventListener("mousedown", (event) => {
                event.preventDefault();
                choose(option);
            });
            menu.appendChild(item);
        });
    }

    function openMenu() {
        render(input.value === selectedLabel() ? "" : input.value);
        menu.hidden = false;
        input.setAttribute("aria-expanded", "true");
    }

    function closeMenu() {
        menu.hidden = true;
        input.setAttribute("aria-expanded", "false");
        activeIndex = -1;
    }

    function selectedLabel() {
        const selected = options.find((option) => option.value === select.value);
        return selected ? selected.text.trim() : "";
    }

    function setActive(index) {
        const items = menu.querySelectorAll(".search-select__option");
        items.forEach((item) => item.classList.remove("search-select__option--active"));
        if (!items.length) return;
        activeIndex = (index + items.length) % items.length;
        items[activeIndex].classList.add("search-select__option--active");
        items[activeIndex].scrollIntoView({ block: "nearest" });
    }

    input.value = selectedLabel();
    input.addEventListener("focus", openMenu);
    input.addEventListener("input", () => {
        select.value = "";
        input.setCustomValidity("");
        render(input.value);
        menu.hidden = false;
        input.setAttribute("aria-expanded", "true");
    });
    input.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown") {
            event.preventDefault();
            if (menu.hidden) openMenu();
            setActive(activeIndex + 1);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive(activeIndex - 1);
        } else if (event.key === "Enter" && activeIndex >= 0) {
            event.preventDefault();
            choose(visibleOptions[activeIndex]);
        } else if (event.key === "Escape") {
            closeMenu();
        }
    });
    input.addEventListener("blur", () => {
        window.setTimeout(() => {
            closeMenu();
            if (!select.value) {
                input.value = "";
                if (wasRequired) input.setCustomValidity("Select a student from the list.");
            }
        }, 100);
    });
}
