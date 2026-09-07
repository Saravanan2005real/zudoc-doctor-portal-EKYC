document.getElementById('customer-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = document.getElementById('submit-btn');
    const alertBox = document.getElementById('alert-box');
    
    submitBtn.textContent = 'Submitting Request...';
    submitBtn.disabled = true;
    alertBox.style.display = 'none';
    alertBox.className = 'alert';

    const formData = new FormData(form);
    
    // Get selected services
    const selectedServices = [];
    document.querySelectorAll('input[name="services"]:checked').forEach((checkbox) => {
        selectedServices.push(checkbox.value);
    });

    // Combine services into requirements
    let requirementsText = formData.get('requirements');
    if (selectedServices.length > 0) {
        requirementsText = `Requested Services: [${selectedServices.join(', ')}]\n\nDetails: ` + requirementsText;
    }
    
    const data = {
        company_name: formData.get('company_name'),
        contact_name: formData.get('contact_name'),
        contact_email: formData.get('contact_email'),
        industry: formData.get('industry'),
        expected_volume: formData.get('expected_volume'),
        requirements: requirementsText
    };

    try {
        const response = await fetch('/api/v1/b2b/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            alertBox.textContent = result.message || 'Request submitted successfully!';
            alertBox.className = 'alert success';
            alertBox.style.display = 'block';
            form.reset();
        } else {
            alertBox.textContent = result.detail || result.message || 'An error occurred while submitting the request.';
            alertBox.className = 'alert error';
            alertBox.style.display = 'block';
        }
    } catch (err) {
        alertBox.textContent = 'Network error. Please try again later.';
        alertBox.className = 'alert error';
        alertBox.style.display = 'block';
    } finally {
        submitBtn.textContent = 'Request Pipeline';
        submitBtn.disabled = false;
    }
});
