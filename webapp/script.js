// https://viscously-unmeliorated-bibi.ngrok-free.dev

document.addEventListener('DOMContentLoaded', function() {
    const tg = window.Telegram.WebApp;
    tg.expand();

    const loader = document.getElementById('loader');
    const profileCard = document.getElementById('profile-card');
    const createPrompt = document.getElementById('create-prompt');
    const creationFormDiv = document.getElementById('creation-form');
    const form = document.getElementById('form');
    const likeButton = document.getElementById('like-button');
    const likeCounter = document.getElementById('like-counter');
    
    const GET_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/get_profile';
    const LIKE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/like_profile';
    const CREATE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/create_profile';

    let receiverId = null;

    function showProfile(data) {
        receiverId = data.user_id;
        document.getElementById('user-photo').src = data.photo_url;
        document.getElementById('user-name').textContent = data.name;
        document.getElementById('user-age').textContent = `Возраст: ${data.age}`;
        document.getElementById('user-bio').textContent = data.bio;
        likeCounter.textContent = data.likes_count;
        if (data.has_liked || data.is_own_profile) {
            likeButton.classList.add('liked');
            likeButton.disabled = true;
        }
        loader.classList.add('hidden');
        profileCard.classList.remove('hidden');
    }

    function showCreationPrompt() {
        loader.classList.add('hidden');
        profileCard.classList.add('hidden');
        createPrompt.classList.remove('hidden');
    }

    fetch(GET_PROFILE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: tg.initData
    })
    .then(response => {
        if (response.status === 404) {
            showCreationPrompt();
            throw new Error('Profile not found, showing creation form.');
        }
        if (!response.ok) { throw new Error(`Network response was not ok, status: ${response.status}`); }
        return response.json();
    })
    .then(data => { showProfile(data); })
    .catch(error => {
        if (error.message.startsWith('Profile not found')) { console.log(error.message); } 
        else {
            console.error('Error fetching profile:', error);
            loader.textContent = 'Сталася помилка мережі. Спробуйте пізніше.';
        }
    });

    likeButton.addEventListener('click', () => {
        if (!receiverId) return;
        likeButton.disabled = true;
        fetch(LIKE_PROFILE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: tg.initData, receiver_id: receiverId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                likeCounter.textContent = parseInt(likeCounter.textContent) + 1;
                likeButton.classList.add('liked');
            } else {
                likeButton.disabled = false;
                tg.showAlert(data.message || 'Не удалось поставить лайк.');
            }
        });
    });

    document.getElementById('create-button').addEventListener('click', () => {
        createPrompt.classList.add('hidden');
        creationFormDiv.classList.remove('hidden');
    });
    
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData();
        formData.append('initData', tg.initData);
        formData.append('name', document.getElementById('name-input').value);
        formData.append('age', document.getElementById('age-input').value);
        formData.append('bio', document.getElementById('bio-input').value);
        formData.append('photo', document.getElementById('photo-input').files[0]);
        tg.MainButton.showProgress();
        fetch(CREATE_PROFILE_URL, { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            tg.MainButton.hideProgress();
            if (data.success) {
                tg.showAlert('Твій профіль успішно створено!', () => { window.location.reload(); });
            } else {
                tg.showAlert(data.message || 'Ошибка при создании профиля.');
            }
        });
    });
});