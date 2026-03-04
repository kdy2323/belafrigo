document.addEventListener("DOMContentLoaded", () => {
    const card = document.querySelector(".card");
    card.style.opacity = 0;
    card.style.transform = "translateY(30px)";
    card.style.transition = "all 0.6s ease-out";
    setTimeout(() => {
        card.style.opacity = 1;
        card.style.transform = "translateY(0)";
    }, 200);
});