(() => {
 const nivel = document.getElementById('id_nivel_estudo');
 const serie = document.getElementById('id_serie');
 if (!nivel || !serie) return;
 const groups = [...serie.querySelectorAll('optgroup')].map(g => ({label:g.label, options:[...g.children].map(o=>({value:o.value,text:o.textContent}))}));
 const roles = [...document.querySelectorAll('[name=user_type]')];
 const update = () => {
   const previous = serie.value;
   const index = {FUNDAMENTAL:0,MEDIO:1,GRADUACAO:2}[nivel.value];
   serie.replaceChildren(new Option(nivel.value === 'GRADUACAO' ? 'Selecione seu período' : 'Selecione sua série', ''));
   if (index !== undefined) groups[index].options.forEach(o => serie.add(new Option(o.text,o.value)));
   serie.value = [...serie.options].some(o=>o.value===previous) ? previous : '';
   const student = roles.some(r=>r.checked && r.value==='estudante');
   nivel.required = student;
   serie.required = student;
   serie.disabled = !student || index === undefined;
   document.querySelector('label[for=id_serie]').textContent = nivel.value === 'GRADUACAO' ? 'Período:' : 'Série:';
 };
 nivel.addEventListener('change', update);
 roles.forEach(r=>r.addEventListener('change', update));
 update();
})();
