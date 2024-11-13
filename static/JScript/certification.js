function switchToEditMode(rut) {
    document.getElementById(`viewMode${rut}`).style.display = 'none';
    document.getElementById(`editMode${rut}`).style.display = 'block';
}

function addCertification(rut) {
    const container = document.getElementById(`certificationsContainer${rut}`);
    const newCertification = document.createElement('div');
    newCertification.classList.add('row', 'mb-3', 'certification-entry');
    newCertification.innerHTML = `
        <div class="col">
            <select class="form-select" name="certificaciones[][id]" required>
                {% for cert_option in certificaciones %}
                    <option value="{{ cert_option.id }}">{{ cert_option.nombre_capacitacion }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="col">
            <input type="date" class="form-control" name="certificaciones[][fecha_inicio]" required>
        </div>
        <div class="col">
            <input type="date" class="form-control" name="certificaciones[][fecha_fin]" required>
        </div>
        <div class="col">
            <button type="button" class="btn btn-danger" onclick="removeCertification(this)">Eliminar</button>
        </div>
    `;
    container.appendChild(newCertification);
}

function removeCertification(button) {
    button.closest('.certification-entry').remove();
}
