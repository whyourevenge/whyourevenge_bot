// Коли сторінка повністю завантажилась
document.addEventListener('DOMContentLoaded', function() {
    const tg = window.Telegram.WebApp;
    tg.expand(); // Розширюємо Web App на весь екран

    const loader = document.getElementById('loader');
    const profileCard = document.getElementById('profile-card');

    // Адреса, на якій наш бот буде чекати запит
    // ВАЖЛИВО: поки що це просто заглушка, ми замінимо її пізніше
    const BACKEND_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/get_profile'; 

    // Перевіряємо, чи є дані для ініціалізації
    if (!tg.initData) {
        loader.textContent = 'Помилка: Не вдалося отримати дані користувача. Будь ласка, запустіть з клієнта Telegram.';
        return;
    }

    // Відправляємо запит на наш бекенд (до бота)
    fetch(BACKEND_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        // Відправляємо дані, які Telegram надає для безпечної ідентифікації
        body: JSON.stringify({ initData: tg.initData })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            loader.textContent = data.message || 'Не вдалося завантажити профіль.';
        } else {
            // Якщо все добре, заповнюємо картку даними
            document.getElementById('user-photo').src = data.photo_url;
            document.getElementById('user-name').textContent = data.name;
            document.getElementById('user-age').textContent = `Вік: ${data.age}`;
            document.getElementById('user-bio').textContent = data.bio;
            
            // Ховаємо завантажувач і показуємо картку
            loader.classList.add('hidden');
            profileCard.classList.remove('hidden');
        }
    })
    .catch(error => {
        console.error('Error fetching profile:', error);
        loader.textContent = 'Сталася помилка мережі. Спробуйте пізніше.';
    });
});