    document.addEventListener("DOMContentLoaded", () => {
        // Animation fade-in pour le titre
        const title = document.getElementById("title");
        title.style.opacity = 0;
        title.style.transition = "opacity 1.5s ease-in-out";
        setTimeout(() => title.style.opacity = 1, 200);

        // Animation cartes avec delay
        const cards = document.querySelectorAll(".hover-scale");
        cards.forEach((card, i) => {
            card.style.transform = "scale(0.8)";
            card.style.opacity = 0;
            card.style.transition = "all 0.5s ease-in-out";
            setTimeout(() => {
                card.style.transform = "scale(1)";
                card.style.opacity = 1;
            }, 400 + i*200);

            // Hover dynamique
            card.addEventListener("mouseover", () => card.style.transform = "scale(1.05)");
            card.addEventListener("mouseout", () => card.style.transform = "scale(1)");
        });
    });

    