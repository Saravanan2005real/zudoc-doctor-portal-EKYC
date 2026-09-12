document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-verification-btn');
    const linkInput = document.getElementById('verify-link-input');

    startBtn.addEventListener('click', () => {
        const link = linkInput.value.trim();

        if (!link) {
            alert('Please paste a valid Verifyyy pipeline link to simulate the integration.');
            return;
        }

        // Add a query param to simulate returning to the swiggy app (optional logic on the verifyyy side)
        const redirectUrl = encodeURIComponent(window.location.href);
        let finalLink = link;
        if (link.includes('?')) {
            finalLink += `&return_url=${redirectUrl}`;
        } else {
            finalLink += `?return_url=${redirectUrl}`;
        }

        // Change button state
        startBtn.textContent = 'Redirecting...';
        startBtn.disabled = true;
        startBtn.style.opacity = '0.7';

        // Simulate a small loading delay for realism
        setTimeout(() => {
            window.location.href = finalLink;
        }, 600);
    });
});
