document.getElementById('b2b-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const alertBox = document.getElementById('alert-box');
    
    // Reset alert
    alertBox.style.display = 'none';
    alertBox.className = 'alert';
    
    // Collect data
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    submitBtn.textContent = 'Submitting...';
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/v1/b2b/requests', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            alertBox.textContent = result.message || 'Application submitted successfully!';
            alertBox.classList.add('success');
            alertBox.style.display = 'block';
            form.reset();
        } else {
            alertBox.textContent = result.detail || result.message || 'Failed to submit application.';
            alertBox.classList.add('error');
            alertBox.style.display = 'block';
        }
    } catch (error) {
        alertBox.textContent = 'A network error occurred. Please try again.';
        alertBox.classList.add('error');
        alertBox.style.display = 'block';
    } finally {
        submitBtn.textContent = 'Submit Request';
        submitBtn.disabled = false;
    }
});
