/* UI language switching. User supplied lecture content stays in its spoken language. */
(() => {
  const normalize = value => String(value).replace(/\s+/g,' ').trim();
  const locales = {
    ru: {
      'Язык интерфейса':'Язык интерфейса','ЗНАНИЯ — НАЙДЕНЫ':'ЗНАНИЯ — НАЙДЕНЫ','В каждой лекции':'В каждой лекции','есть ':'есть ','ответ.':'ответ.','Ищите идеи и объяснения, а не отдельные слова.':'Ищите идеи и объяснения, а не отдельные слова.','Мы покажем нужный момент и поможем разобраться.':'Мы покажем нужный момент и поможем разобраться.','Нажмите на лупу,':'Нажмите на лупу,','чтобы найти идею':'чтобы найти идею','идея найдена':'идея найдена','СЕМАНТИЧЕСКИЙ ПОИСК':'СЕМАНТИЧЕСКИЙ ПОИСК','Ищет по всем готовым лекциям':'Ищет по всем готовым лекциям','Найти':'Найти','ВАША БИБЛИОТЕКА':'ВАША БИБЛИОТЕКА','Лекции ':'Лекции ','Добавить лекцию':'Добавить лекцию','Начните с первой лекции':'Начните с первой лекции','Загрузите видео — мы подготовим транскрипт, главы и смысловой поиск.':'Загрузите видео — мы подготовим транскрипт, главы и смысловой поиск.','ЛИЦЕНЗИЯ И УСЛОВИЯ ИСПОЛЬЗОВАНИЯ':'ЛИЦЕНЗИЯ И УСЛОВИЯ ИСПОЛЬЗОВАНИЯ','Язык речи в видео':'Язык речи в видео','Выберите язык, на котором говорят в видео. Язык интерфейса меняется отдельно.':'Выберите язык, на котором говорят в видео. Язык интерфейса меняется отдельно.','Название лекции':'Название лекции','Папка для лекции':'Папка для лекции','＋ Новая папка':'＋ Новая папка','Без папки (основная библиотека)':'Без папки (основная библиотека)','Отмена':'Отмена','Создастся новая папка, и файл сразу будет перемещён в неё.':'Создастся новая папка, и файл сразу будет перемещён в неё.','Перетащите видео сюда':'Перетащите видео сюда','или ':'или ','выберите файл':'выберите файл','Ссылка':'Ссылка','Файл видео':'Файл видео','Ссылка на видео':'Ссылка на видео','Качество видео':'Качество видео','Лучшее доступное':'Лучшее доступное','Начать обработку ':'Начать обработку ','Отменить загрузку':'Отменить загрузку','Личный кабинет':'Личный кабинет','ЛИЧНОЕ ПРОСТРАНСТВО':'ЛИЧНОЕ ПРОСТРАНСТВО','С возвращением':'С возвращением','Войдите, чтобы открыть свою библиотеку лекций.':'Войдите, чтобы открыть свою библиотеку лекций.','Войти':'Войти','Создать аккаунт':'Создать аккаунт','Логин':'Логин','Пароль':'Пароль','Введите логин и пароль вашего кабинета.':'Введите логин и пароль вашего кабинета.','ВАШ АККАУНТ':'ВАШ АККАУНТ','Свои буквы':'Свои буквы','Сохранить':'Сохранить','Загрузить своё фото':'Загрузить своё фото','лекций':'лекций','готово':'готово','Изменить пароль':'Изменить пароль','Выйти из аккаунта ':'Выйти из аккаунта ','ПЕРЕМЕСТИТЬ ЛЕКЦИЮ':'ПЕРЕМЕСТИТЬ ЛЕКЦИЮ','Переместить лекцию':'Переместить лекцию','Выберите папку или создайте новую.':'Выберите папку или создайте новую.','Или создать новую папку':'Или создать новую папку','Создать и переместить ':'Создать и переместить ','Оглавление':'Оглавление','Краткий пересказ':'Краткий пересказ','Обновить пересказ и главы':'Обновить пересказ и главы','Перераспознать речь':'Перераспознать речь','Транскрипт':'Транскрипт','Главы':'Главы','Удалить лекцию':'Удалить лекцию','Администрирование':'Администрирование','Аккаунты':'Аккаунты','Видео на сервере':'Видео на сервере','Настройки':'Настройки','Создать папку':'Создать папку','Новая папка':'Новая папка','Собрать лекции вместе':'Собрать лекции вместе','Дайте папке короткое название. Лекции можно будет перемещать из карточки каждой записи.':'Дайте папке короткое название. Лекции можно будет перемещать из карточки каждой записи.','Название папки':'Название папки','Создать папку ':'Создать папку ','Папки с лекциями':'Папки с лекциями'
    },
    en: {
      'Язык интерфейса':'Interface language','ЗНАНИЯ — НАЙДЕНЫ':'KNOWLEDGE — FOUND','В каждой лекции':'Every lecture has','есть ':'an ','ответ.':'answer.','Ищите идеи и объяснения, а не отдельные слова.':'Search for ideas and explanations, not just words.','Мы покажем нужный момент и поможем разобраться.':'We’ll find the right moment and help you understand.','Нажмите на лупу,':'Click the magnifier','чтобы найти идею':'to find an idea','идея найдена':'idea found','СЕМАНТИЧЕСКИЙ ПОИСК':'SEMANTIC SEARCH','Ищет по всем готовым лекциям':'Searches all processed lectures','Найти':'Search','ВАША БИБЛИОТЕКА':'YOUR LIBRARY','Лекции ':'Lectures ','Добавить лекцию':'Add a lecture','Начните с первой лекции':'Start with your first lecture','Загрузите видео — мы подготовим транскрипт, главы и смысловой поиск.':'Upload a video to create a transcript, chapters and semantic search.','ЛИЦЕНЗИЯ И УСЛОВИЯ ИСПОЛЬЗОВАНИЯ':'LICENSE AND TERMS OF USE','Язык речи в видео':'Spoken language in the video','Выберите язык, на котором говорят в видео. Язык интерфейса меняется отдельно.':'Choose the language spoken in the video. Interface language is selected separately.','Название лекции':'Lecture title','Папка для лекции':'Lecture folder','＋ Новая папка':'＋ New folder','Без папки (основная библиотека)':'No folder (main library)','Отмена':'Cancel','Создастся новая папка, и файл сразу будет перемещён в неё.':'A new folder will be created and the file moved into it.','Перетащите видео сюда':'Drop a video here','или ':'or ','выберите файл':'choose a file','Ссылка':'Link','Файл видео':'Video file','Ссылка на видео':'Video link','Качество видео':'Video quality','Лучшее доступное':'Best available','Начать обработку ':'Start processing ','Отменить загрузку':'Cancel upload','Личный кабинет':'My account','ЛИЧНОЕ ПРОСТРАНСТВО':'YOUR SPACE','С возвращением':'Welcome back','Войдите, чтобы открыть свою библиотеку лекций.':'Sign in to open your lecture library.','Войти':'Sign in','Создать аккаунт':'Create account','Логин':'Username','Пароль':'Password','Введите логин и пароль вашего кабинета.':'Enter your account username and password.','ВАШ АККАУНТ':'YOUR ACCOUNT','Свои буквы':'Your initials','Сохранить':'Save','Загрузить своё фото':'Upload your photo','лекций':'lectures','готово':'ready','Изменить пароль':'Change password','Выйти из аккаунта ':'Sign out ','ПЕРЕМЕСТИТЬ ЛЕКЦИЮ':'MOVE LECTURE','Переместить лекцию':'Move lecture','Выберите папку или создайте новую.':'Choose a folder or create one.','Или создать новую папку':'Or create a new folder','Создать и переместить ':'Create and move ','Оглавление':'Outline','Краткий пересказ':'Summary','Обновить пересказ и главы':'Refresh summary and chapters','Перераспознать речь':'Re-transcribe speech','Транскрипт':'Transcript','Главы':'Chapters','Удалить лекцию':'Delete lecture','Администрирование':'Administration','Аккаунты':'Accounts','Видео на сервере':'Server videos','Настройки':'Settings','Создать папку':'Create folder','Новая папка':'New folder','Собрать лекции вместе':'Group your lectures','Дайте папке короткое название. Лекции можно будет перемещать из карточки каждой записи.':'Give the folder a short name. You can move lectures into it from each lecture card.','Название папки':'Folder name','Создать папку ':'Create folder ','Папки с лекциями':'Lecture folders'
    },
    zh: {
      'Язык интерфейса':'界面语言','ЗНАНИЯ — НАЙДЕНЫ':'知识，已找到','В каждой лекции':'每堂课中都有','есть ':'','ответ.':'答案。','Ищите идеи и объяснения, а не отдельные слова.':'搜索观点和解释，而不只是单个词。','Мы покажем нужный момент и поможем разобраться.':'我们会定位相关片段，帮助您理解。','Нажмите на лупу,':'点击放大镜','чтобы найти идею':'查找观点','идея найдена':'已找到观点','СЕМАНТИЧЕСКИЙ ПОИСК':'语义搜索','Ищет по всем готовым лекциям':'搜索所有已处理的课程','Найти':'搜索','ВАША БИБЛИОТЕКА':'您的资料库','Лекции ':'课程 ','Добавить лекцию':'添加课程','Начните с первой лекции':'从第一堂课开始','Загрузите видео — мы подготовим транскрипт, главы и смысловой поиск.':'上传视频，即可生成转录、章节和语义搜索。','ЛИЦЕНЗИЯ И УСЛОВИЯ ИСПОЛЬЗОВАНИЯ':'许可证与使用条款','Язык речи в видео':'视频语音语言','Выберите язык, на котором говорят в видео. Язык интерфейса меняется отдельно.':'请选择视频中的语音语言。界面语言单独设置。','Название лекции':'课程名称','Папка для лекции':'课程文件夹','＋ Новая папка':'＋ 新建文件夹','Без папки (основная библиотека)':'无文件夹（主资料库）','Отмена':'取消','Создастся новая папка, и файл сразу будет перемещён в неё。':'将创建文件夹并移动此文件。','Перетащите видео сюда':'将视频拖到此处','или ':'或','выберите файл':'选择文件','Ссылка':'链接','Файл видео':'视频文件','Ссылка на видео':'视频链接','Качество видео':'视频画质','Лучшее доступное':'最佳可用','Начать обработку ':'开始处理 ','Отменить загрузку':'取消上传','Личный кабинет':'个人账户','ЛИЧНОЕ ПРОСТРАНСТВО':'个人空间','С возвращением':'欢迎回来','Войдите, чтобы открыть свою библиотеку лекций.':'登录以打开您的课程资料库。','Войти':'登录','Создать аккаунт':'创建账户','Логин':'用户名','Пароль':'密码','Введите логин и пароль вашего кабинета.':'输入账户用户名和密码。','ВАШ АККАУНТ':'您的账户','Свои буквы':'自定义字母','Сохранить':'保存','Загрузить своё фото':'上传头像','лекций':'堂课程','готово':'已完成','Изменить пароль':'更改密码','Выйти из аккаунта ':'退出账户 ','ПЕРЕМЕСТИТЬ ЛЕКЦИЮ':'移动课程','Переместить лекцию':'移动课程','Выберите папку или создайте новую.':'选择文件夹或新建文件夹。','Или создать новую папку':'或新建文件夹','Создать и переместить ':'创建并移动 ','Оглавление':'目录','Краткий пересказ':'摘要','Обновить пересказ и главы':'更新摘要和章节','Перераспознать речь':'重新转录语音','Транскрипт':'转录文本','Главы':'章节','Удалить лекцию':'删除课程','Администрирование':'管理','Аккаунты':'账户','Видео на сервере':'服务器视频','Настройки':'设置','Создать папку':'新建文件夹','Новая папка':'新建文件夹','Собрать лекции вместе':'整理课程','Дайте папке короткое название. Лекции можно будет перемещать из карточки каждой записи.':'为文件夹设置简短名称，之后可从课程卡片移动课程。','Название папки':'文件夹名称','Создать папку ':'创建文件夹 ','Папки с лекциями':'课程文件夹'
    },
    de: {
      'Язык интерфейса':'Oberflächensprache','ЗНАНИЯ — НАЙДЕНЫ':'WISSEN — GEFUNDEN','В каждой лекции':'In jeder Vorlesung gibt es','есть ':'eine ','ответ.':'Antwort.','Ищите идеи и объяснения, а не отдельные слова.':'Suchen Sie nach Ideen und Erklärungen statt nach einzelnen Wörtern.','Мы покажем нужный момент и поможем разобраться.':'Wir zeigen den passenden Moment und helfen beim Verständnis.','Нажмите на лупу,':'Klicken Sie auf die Lupe,','чтобы найти идею':'um eine Idee zu finden','идея найдена':'Idee gefunden','СЕМАНТИЧЕСКИЙ ПОИСК':'SEMANTISCHE SUCHE','Ищет по всем готовым лекциям':'Durchsucht alle verarbeiteten Vorlesungen','Найти':'Suchen','ВАША БИБЛИОТЕКА':'IHRE BIBLIOTHEK','Лекции ':'Vorlesungen ','Добавить лекцию':'Vorlesung hinzufügen','Начните с первой лекции':'Beginnen Sie mit Ihrer ersten Vorlesung','Загрузите видео — мы подготовим транскрипт, главы и смысловой поиск.':'Laden Sie ein Video hoch, um Transkript, Kapitel und semantische Suche zu erstellen.','ЛИЦЕНЗИЯ И УСЛОВИЯ ИСПОЛЬЗОВАНИЯ':'LIZENZ UND NUTZUNGSBEDINGUNGEN','Язык речи в видео':'Gesprochene Sprache im Video','Выберите язык, на котором говорят в видео. Язык интерфейса меняется отдельно.':'Wählen Sie die Sprache des Videos. Die Oberflächensprache wird separat eingestellt.','Название лекции':'Vorlesungstitel','Папка для лекции':'Vorlesungsordner','＋ Новая папка':'＋ Neuer Ordner','Без папки (основная библиотека)':'Kein Ordner (Hauptbibliothek)','Отмена':'Abbrechen','Создастся новая папка, и файл сразу будет перемещён в неё.':'Ein neuer Ordner wird erstellt und die Datei dorthin verschoben.','Перетащите видео сюда':'Video hier ablegen','или ':'oder ','выберите файл':'Datei auswählen','Ссылка':'Link','Файл видео':'Videodatei','Ссылка на видео':'Videolink','Качество видео':'Videoqualität','Лучшее доступное':'Beste verfügbare','Начать обработку ':'Verarbeitung starten ','Отменить загрузку':'Upload abbrechen','Личный кабинет':'Mein Konto','ЛИЧНОЕ ПРОСТРАНСТВО':'IHR BEREICH','С возвращением':'Willkommen zurück','Войдите, чтобы открыть свою библиотеку лекций.':'Melden Sie sich an, um Ihre Vorlesungsbibliothek zu öffnen.','Войти':'Anmelden','Создать аккаунт':'Konto erstellen','Логин':'Benutzername','Пароль':'Passwort','Введите логин и пароль вашего кабинета.':'Geben Sie Ihren Benutzernamen und Ihr Passwort ein.','ВАШ АККАУНТ':'IHR KONTO','Свои буквы':'Eigene Initialen','Сохранить':'Speichern','Загрузить своё фото':'Eigenes Foto hochladen','лекций':'Vorlesungen','готово':'fertig','Изменить пароль':'Passwort ändern','Выйти из аккаунта ':'Abmelden ','ПЕРЕМЕСТИТЬ ЛЕКЦИЮ':'VORLESUNG VERSCHIEBEN','Переместить лекцию':'Vorlesung verschieben','Выберите папку или создайте новую.':'Wählen Sie einen Ordner oder erstellen Sie einen neuen.','Или создать новую папку':'Oder neuen Ordner erstellen','Создать и переместить ':'Erstellen und verschieben ','Оглавление':'Gliederung','Краткий пересказ':'Zusammenfassung','Обновить пересказ и главы':'Zusammenfassung und Kapitel aktualisieren','Перераспознать речь':'Sprache erneut erkennen','Транскрипт':'Transkript','Главы':'Kapitel','Удалить лекцию':'Vorlesung löschen','Администрирование':'Administration','Аккаунты':'Konten','Видео на сервере':'Servervideos','Настройки':'Einstellungen','Создать папку':'Ordner erstellen','Новая папка':'Neuer Ordner','Собрать лекции вместе':'Vorlesungen sammeln','Дайте папке короткое название. Лекции можно будет перемещать из карточки каждой записи.':'Geben Sie dem Ordner einen kurzen Namen. Vorlesungen lassen sich später über ihre Karten verschieben.','Название папки':'Ordnername','Создать папку ':'Ordner erstellen ','Папки с лекциями':'Vorlesungsordner'
    },
    es: {
      'Язык интерфейса':'Idioma de la interfaz','ЗНАНИЯ — НАЙДЕНЫ':'CONOCIMIENTO — ENCONTRADO','В каждой лекции':'Cada clase tiene una','есть ':' ','ответ.':'respuesta.','Ищите идеи и объяснения, а не отдельные слова.':'Busca ideas y explicaciones, no solo palabras sueltas.','Мы покажем нужный момент и поможем разобраться.':'Encontraremos el momento adecuado y te ayudaremos a entenderlo.','Нажмите на лупу,':'Pulsa la lupa','чтобы найти идею':'para encontrar una idea','идея найдена':'idea encontrada','СЕМАНТИЧЕСКИЙ ПОИСК':'BÚSQUEDA SEMÁNTICA','Ищет по всем готовым лекциям':'Busca en todas las clases procesadas','Найти':'Buscar','ВАША БИБЛИОТЕКА':'TU BIBLIOTECA','Лекции ':'Clases ','Добавить лекцию':'Añadir clase','Начните с первой лекции':'Empieza con tu primera clase','Загрузите видео — мы подготовим транскрипт, главы и смысловой поиск.':'Sube un vídeo para crear la transcripción, los capítulos y la búsqueda semántica.','ЛИЦЕНЗИЯ И УСЛОВИЯ ИСПОЛЬЗОВАНИЯ':'LICENCIA Y CONDICIONES DE USO','Язык речи в видео':'Idioma hablado en el vídeo','Выберите язык, на котором говорят в видео. Язык интерфейса меняется отдельно.':'Elige el idioma hablado en el vídeo. El idioma de la interfaz se configura por separado.','Название лекции':'Título de la clase','Папка для лекции':'Carpeta de la clase','＋ Новая папка':'＋ Nueva carpeta','Без папки (основная библиотека)':'Sin carpeta (biblioteca principal)','Отмена':'Cancelar','Создастся новая папка, и файл сразу будет перемещён в неё.':'Se creará una carpeta nueva y el archivo se moverá a ella.','Перетащите видео сюда':'Arrastra el vídeo aquí','или ':'o ','выберите файл':'elige un archivo','Ссылка':'Enlace','Файл видео':'Archivo de vídeo','Ссылка на видео':'Enlace del vídeo','Качество видео':'Calidad del vídeo','Лучшее доступное':'La mejor disponible','Начать обработку ':'Iniciar procesamiento ','Отменить загрузку':'Cancelar carga','Личный кабинет':'Mi cuenta','ЛИЧНОЕ ПРОСТРАНСТВО':'TU ESPACIO','С возвращением':'Te damos la bienvenida','Войдите, чтобы открыть свою библиотеку лекций.':'Inicia sesión para abrir tu biblioteca de clases.','Войти':'Iniciar sesión','Создать аккаунт':'Crear cuenta','Логин':'Usuario','Пароль':'Contraseña','Введите логин и пароль вашего кабинета.':'Introduce el usuario y la contraseña de tu cuenta.','ВАШ АККАУНТ':'TU CUENTA','Свои буквы':'Tus iniciales','Сохранить':'Guardar','Загрузить своё фото':'Subir una foto','лекций':'clases','готово':'listas','Изменить пароль':'Cambiar contraseña','Выйти из аккаунта ':'Cerrar sesión ','ПЕРЕМЕСТИТЬ ЛЕКЦИЮ':'MOVER CLASE','Переместить лекцию':'Mover clase','Выберите папку или создайте новую.':'Elige una carpeta o crea una nueva.','Или создать новую папку':'O crear una carpeta nueva','Создать и переместить ':'Crear y mover ','Оглавление':'Índice','Краткий пересказ':'Resumen','Обновить пересказ и главы':'Actualizar resumen y capítulos','Перераспознать речь':'Volver a transcribir','Транскрипт':'Transcripción','Главы':'Capítulos','Удалить лекцию':'Eliminar clase','Администрирование':'Administración','Аккаунты':'Cuentas','Видео на сервере':'Vídeos del servidor','Настройки':'Configuración','Создать папку':'Crear carpeta','Новая папка':'Nueva carpeta','Собрать лекции вместе':'Agrupa tus clases','Дайте папке короткое название. Лекции можно будет перемещать из карточки каждой записи.':'Pon un nombre corto a la carpeta. Después podrás mover clases desde su ficha.','Название папки':'Nombre de la carpeta','Создать папку ':'Crear carpeta ','Папки с лекциями':'Carpetas de clases'
    }
  };
  const extraRows=[
    ['БИБЛИОТЕКА','LIBRARY','图书馆','BIBLIOTHEK','BIBLIOTECA'],
    ['Все лекции','All lectures','所有课程','Alle Vorlesungen','Todas las clases'],
    ['Свернуть меню','Collapse menu','收起菜单','Menü einklappen','Contraer menú'],
    ['Развернуть меню','Expand menu','展开菜单','Menü ausklappen','Expandir menú'],
    ['Как устроен проект','How it works','项目介绍','So funktioniert das Projekt','Cómo funciona'],
    ['Например, Введение в машинное обучение','For example, Introduction to machine learning','例如：机器学习导论','Zum Beispiel: Einführung in maschinelles Lernen','Por ejemplo: Introducción al aprendizaje automático'],
    ['Поддерживаются YouTube, VK Видео, Rutube и многие платформы yt-dlp. Доступные разрешения зависят от ролика.','YouTube, VK Video, Rutube and many yt-dlp platforms are supported. Available resolutions depend on the video.','支持 YouTube、VK Video、Rutube 和许多 yt-dlp 平台。可用清晰度取决于视频。','YouTube, VK Video, Rutube und viele yt-dlp-Plattformen werden unterstützt. Die verfügbaren Auflösungen hängen vom Video ab.','Se admiten YouTube, VK Video, Rutube y muchas plataformas de yt-dlp. La resolución disponible depende del vídeo.'],
    ['Переместить в папку','Move to folder','移动到文件夹','In Ordner verschieben','Mover a carpeta'],
    ['С начала','From the beginning','从头开始','Von Anfang an','Desde el principio'],
    ['ГОТОВА','READY','已就绪','BEREIT','LISTA'],
    ['ОШИБКА','ERROR','错误','FEHLER','ERROR'],
    ['ОБРАБОТКА','PROCESSING','处理中','IN BEARBEITUNG','PROCESANDO'],
    ['ГОТОВИТСЯ','QUEUED','排队中','IN WARTESCHLANGE','EN COLA'],
    ['лучшее доступное','best available','最佳可用','beste verfügbare','la mejor disponible'],
    ['Краткий конспект','Short notes','简要笔记','Kurze Notizen','Apuntes breves'],
    ['Краткий пересказ','Short summary','简短摘要','Kurze Zusammenfassung','Resumen breve'],
    ['Загружаем транскрипт…','Loading transcript…','正在加载转录文本…','Transkript wird geladen…','Cargando transcripción…'],
    ['Разделы появятся после обработки.','Chapters will appear after processing.','处理完成后将显示章节。','Kapitel erscheinen nach der Verarbeitung.','Los capítulos aparecerán al terminar el procesamiento.'],
    ['Разделы не найдены.','No chapters found.','未找到章节。','Keine Kapitel gefunden.','No se encontraron capítulos.'],
    ['Составляем…','Creating…','正在生成…','Wird erstellt…','Creando…'],
    ['Готово','Done','完成','Fertig','Listo'],
    ['Сохраняем…','Saving…','正在保存…','Wird gespeichert…','Guardando…'],
    ['Аватар сохранён','Avatar saved','头像已保存','Avatar gespeichert','Avatar guardado'],
    ['Лекция не найдена','Lecture not found','未找到课程','Vorlesung nicht gefunden','Clase no encontrada'],
    ['Лекция по ссылке','Lecture from link','链接课程','Vorlesung über Link','Clase desde enlace'],
    ['Загрузка модели распознавания','Loading speech model','正在加载语音识别模型','Spracherkennungsmodell wird geladen','Cargando el modelo de voz']
    ,['НОВАЯ ЛЕКЦИЯ','NEW LECTURE','新课程','NEUE VORLESUNG','NUEVA CLASE']
    ,['Загрузите видео или вставьте ссылку — остальное мы сделаем сами.','Upload a video or paste a link — we’ll take care of the rest.','上传视频或粘贴链接，其余交给我们。','Lade ein Video hoch oder füge einen Link ein — wir kümmern uns um den Rest.','Sube un vídeo o pega un enlace; nosotros nos encargamos del resto.']
    ,['· MP4, WebM · до 500 МБ','· MP4, WebM · up to 500 MB','· MP4、WebM · 最大 500 MB','· MP4, WebM · bis zu 500 MB','· MP4, WebM · hasta 500 MB']
    ,['До 2160p · 4K','Up to 2160p · 4K','最高 2160p · 4K','Bis zu 2160p · 4K','Hasta 2160p · 4K']
    ,['До 1440p','Up to 1440p','最高 1440p','Bis zu 1440p','Hasta 1440p']
    ,['До 1080p · Full HD','Up to 1080p · Full HD','最高 1080p · Full HD','Bis zu 1080p · Full HD','Hasta 1080p · Full HD']
    ,['До 720p · HD','Up to 720p · HD','最高 720p · HD','Bis zu 720p · HD','Hasta 720p · HD']
    ,['До 480p','Up to 480p','最高 480p','Bis zu 480p','Hasta 480p']
    ,['До 360p','Up to 360p','最高 360p','Bis zu 360p','Hasta 360p']
    ,['НОВАЯ ПАПКА','NEW FOLDER','新建文件夹','NEUER ORDNER','NUEVA CARPETA']
    ,['У каждой учётной записи своя библиотека. Содержимое хранится в зашифрованном виде.','Each account has its own library. Its contents are stored encrypted.','每个账户都有自己的资料库，内容经过加密存储。','Jedes Konto hat eine eigene Bibliothek. Die Inhalte werden verschlüsselt gespeichert.','Cada cuenta tiene su propia biblioteca. El contenido se almacena cifrado.']
    ,['Используя Лекторий, вы принимаете','By using Lectorium, you accept the','使用 Lectorium 即表示您接受','Mit der Nutzung von Lectorium akzeptierst du die','Al usar Lectorium, aceptas las']
    ,['условия использования','terms of use','使用条款','Nutzungsbedingungen','condiciones de uso']
    ,['Пользователь','User','用户','Benutzer','Usuario']
    ,['Личная библиотека лекций','Personal lecture library','个人课程资料库','Persönliche Vorlesungsbibliothek','Biblioteca personal de clases']
    ,['БЕЗОПАСНОСТЬ','SECURITY','安全','SICHERHEIT','SEGURIDAD']
    ,['Новый пароль','New password','新密码','Neues Passwort','Nueva contraseña']
    ,['Подтвердите текущий пароль и задайте новый.','Confirm your current password and choose a new one.','确认当前密码并设置新密码。','Bestätige dein aktuelles Passwort und lege ein neues fest.','Confirma tu contraseña actual y elige una nueva.']
    ,['Текущий пароль','Current password','当前密码','Aktuelles Passwort','Contraseña actual']
    ,['Сохранить пароль','Save password','保存密码','Passwort speichern','Guardar contraseña']
    ,['ДОСТУП К АККАУНТУ','ACCOUNT ACCESS','账户访问','KONTOZUGANG','ACCESO A LA CUENTA']
    ,['Задать новый пароль','Set a new password','设置新密码','Neues Passwort festlegen','Establecer una nueva contraseña']
    ,['УПРАВЛЕНИЕ СИСТЕМОЙ','SYSTEM MANAGEMENT','系统管理','SYSTEMVERWALTUNG','GESTIÓN DEL SISTEMA']
    ,['Загружаем данные…','Loading data…','正在加载数据…','Daten werden geladen…','Cargando datos…']
    ,['Авто','Auto','自动','Auto','Auto']
    ,['Светлая','Light','浅色','Hell','Claro']
    ,['Тёмная','Dark','深色','Dunkel','Oscuro']
    ,['Сменить тему сайта','Change website theme','切换网站主题','Website-Design ändern','Cambiar el tema del sitio']
    ,['Сменить тему сайта: автоматически','Change website theme: automatic','切换网站主题：自动','Website-Design ändern: automatisch','Cambiar el tema del sitio: automático']
    ,['Сменить тему сайта: светлая','Change website theme: light','切换网站主题：浅色','Website-Design ändern: hell','Cambiar el tema del sitio: claro']
    ,['Сменить тему сайта: тёмная','Change website theme: dark','切换网站主题：深色','Website-Design ändern: dunkel','Cambiar el tema del sitio: oscuro']
    ,['Перевести субтитры','Translate subtitles','翻译字幕','Untertitel übersetzen','Traducir subtítulos']
    ,['Переводим субтитры…','Translating subtitles…','正在翻译字幕…','Untertitel werden übersetzt…','Traduciendo subtítulos…']
    ,['Субтитры переведены','Subtitles translated','字幕已翻译','Untertitel übersetzt','Subtítulos traducidos']
    ,['Не удалось перевести субтитры','Subtitle translation failed','字幕翻译失败','Untertitel konnten nicht übersetzt werden','No se pudieron traducir los subtítulos']
    ,['Не удалось перевести эту часть лекции. Повторите попытку.','Could not translate this part of the lecture. Please try again.','无法翻译本段课程，请重试。','Dieser Teil der Vorlesung konnte nicht übersetzt werden. Bitte erneut versuchen.','No se pudo traducir esta parte de la clase. Inténtalo de nuevo.']
    ,['Перевод занял слишком много времени. Повторите попытку.','Translation took too long. Please try again.','翻译耗时过长，请重试。','Die Übersetzung hat zu lange gedauert. Bitte erneut versuchen.','La traducción tardó demasiado. Inténtalo de nuevo.']
    ,['Язык перевода','Translation language','翻译语言','Übersetzungssprache','Idioma de traducción']
    ,['Авто','Auto','自动','Auto','Auto']
    ,['Светлая','Light','浅色','Hell','Claro']
    ,['Тёмная','Dark','深色','Dunkel','Oscuro']
    ,['Перевод','Translation','翻译','Übersetzung','Traducción']
    ,['Сменить тему сайта: автоматически','Change website theme: automatic','切换网站主题：自动','Website-Design ändern: automatisch','Cambiar el tema del sitio: automático']
    ,['Автоматически','Automatic','自动','Automatisch','Automático']
    ,['ЛОКАЛЬНАЯ ДЕМОНСТРАЦИЯ · РАБОТАЕТ БЕЗ ИНТЕРНЕТА','OFFLINE DEMO · WORKS WITHOUT INTERNET','离线演示 · 无需互联网','OFFLINE-DEMO · FUNKTIONIERT OHNE INTERNET','DEMO SIN CONEXIÓN · FUNCIONA SIN INTERNET']
    ,['БИБЛИОТЕКА','LIBRARY','资料库','BIBLIOTHEK','BIBLIOTECA']
    ,['Все лекции','All lectures','所有课程','Alle Vorlesungen','Todas las clases']
    ,['Создать папку','Create folder','新建文件夹','Ordner erstellen','Crear carpeta']
    ,['Офлайн-стенд','Offline demo','离线演示','Offline-Demo','Demo sin conexión']
    ,['Данные примера в комплекте','Sample data included','包含示例数据','Beispieldaten enthalten','Datos de ejemplo incluidos']
    ,['Как устроен проект','How it works','项目介绍','So funktioniert es','Cómo funciona']
    ,['Добавить лекцию','Add a lecture','添加课程','Vorlesung hinzufügen','Añadir clase']
    ,['Философия','Philosophy','哲学','Philosophie','Filosofía']
    ,['ГОТОВА','READY','已完成','FERTIG','LISTA']
    ,['Открыть лекцию','Open lecture','打开课程','Vorlesung öffnen','Abrir clase']
    ,['Транскрипт','Transcript','转录文本','Transkript','Transcripción']
    ,['Главы','Chapters','章节','Kapitel','Capítulos']
    ,['Переместить в папку','Move to folder','移动到文件夹','In Ordner verschieben','Mover a carpeta']
    ,['Личный кабинет','My account','个人账户','Mein Konto','Mi cuenta']
    ,['В каждой лекции','Every lecture has','每堂课中都有','Jede Vorlesung hat','Cada clase tiene']
    ,['ответ.','answer.','答案。','eine Antwort.','una respuesta.']
    ,['Ищите идеи и объяснения, а не отдельные слова.','Search for ideas and explanations, not single words.','搜索观点和解释，而不只是单个词。','Suche nach Ideen und Erklärungen, nicht nach einzelnen Wörtern.','Busca ideas y explicaciones, no solo palabras sueltas.']
    ,['Демо показывает, как устроен путь от видео до знаний.','See how a video becomes searchable knowledge.','查看视频如何转化为可搜索的知识。','Die Demo zeigt, wie aus Videos durchsuchbares Wissen wird.','La demo muestra cómo convertir vídeos en conocimiento consultable.']
    ,['ЛОКАЛЬНЫЙ ПОИСК ПО ТЕКСТУ','LOCAL TEXT SEARCH','本地文本搜索','LOKALE TEXTSUCHE','BÚSQUEDA LOCAL DE TEXTO']
    ,['Например: как Кант объясняет опыт?','For example: how does Kant explain experience?','例如：康德如何解释经验？','Zum Beispiel: Wie erklärt Kant Erfahrung?','Por ejemplo: ¿cómo explica Kant la experiencia?']
    ,['Примеры: Кант · опыт · время','Examples: Kant · experience · time','示例：康德 · 经验 · 时间','Beispiele: Kant · Erfahrung · Zeit','Ejemplos: Kant · experiencia · tiempo']
    ,['ПРИМЕР ДЛЯ ПОКАЗА','DEMO EXAMPLE','演示示例','DEMO-BEISPIEL','EJEMPLO DE DEMOSTRACIÓN']
    ,['ЧТО ПРОИСХОДИТ','HOW IT WORKS','工作原理','SO FUNKTIONIERT ES','CÓMO FUNCIONA']
    ,['От видео — к понятным моментам','From video to useful moments','从视频到关键片段','Vom Video zu wichtigen Momenten','Del vídeo a los momentos clave']
    ,['Загрузка','Upload','上传','Hochladen','Carga']
    ,['Распознавание','Transcription','语音识别','Transkription','Transcripción']
    ,['Навигация','Navigation','导航','Navigation','Navegación']
    ,['В рабочей версии добавляют видеофайл или ссылку на видео.','In the online version, add a video file or link.','在线版支持添加视频文件或链接。','In der Online-Version lassen sich Videodateien oder Links hinzufügen.','En la versión online puedes añadir un archivo o enlace de vídeo.']
    ,['Для русской речи используется GigaAM-v3; английская, китайская, немецкая и испанская распознаются мультиязычной моделью. Язык можно определить автоматически, расшифровка сохраняет таймкоды.','Russian speech uses GigaAM-v3; English, Chinese, German and Spanish use a multilingual model. The video language can be detected automatically, and transcripts keep timestamps.','俄语语音使用 GigaAM-v3；英语、中文、德语和西班牙语使用多语言模型。系统可自动识别视频语言，转录保留时间戳。','Für Russisch kommt GigaAM-v3 zum Einsatz; Englisch, Chinesisch, Deutsch und Spanisch werden mit einem mehrsprachigen Modell erkannt. Die Videosprache lässt sich automatisch erkennen; das Transkript enthält Zeitmarken.','Para ruso se usa GigaAM-v3; inglés, chino, alemán y español utilizan un modelo multilingüe. El idioma del vídeo se detecta automáticamente y la transcripción conserva las marcas de tiempo.']
    ,['Транскрипт, тематические главы и смысловой поиск помогают быстро найти нужный эпизод.','The transcript, topic chapters and semantic search help you find the right moment.','转录文本、主题章节和语义搜索可帮助快速定位片段。','Transkript, Themenkapitel und semantische Suche helfen, passende Stellen schnell zu finden.','La transcripción, los capítulos temáticos y la búsqueda semántica ayudan a encontrar el momento adecuado.']
    ,['В этой офлайн-демонстрации загрузка выключена. Обработка видео доступна в основной версии на сервере.','Uploads are disabled in this offline demo. Video processing is available in the hosted version.','此离线演示不支持上传。视频处理请使用在线版本。','In dieser Offline-Demo sind Uploads deaktiviert. Die Videoverarbeitung ist in der Online-Version verfügbar.','Las cargas están desactivadas en esta demo sin conexión. El procesamiento está disponible en la versión online.']
    ,['В этой папке нет лекций.','This folder has no lectures.','此文件夹中没有课程。','Dieser Ordner enthält keine Vorlesungen.','Esta carpeta no tiene clases.']
    ,['Перевод субтитров требует серверной модели и доступен в основной версии сайта.','Subtitle translation requires the hosted translation model and is available on the main website.','字幕翻译需要服务器模型，请使用正式网站。','Die Untertitelübersetzung benötigt das Servermodell und ist auf der Hauptwebsite verfügbar.','La traducción de subtítulos requiere el modelo del servidor y está disponible en el sitio principal.']
    ,['Краткий конспект','Short summary','简短摘要','Kurze Zusammenfassung','Resumen breve']
    ,['Аватар','Avatar','头像','Avatar','Avatar']
    ,['Без папки','No folder','未分类','Ohne Ordner','Sin carpeta']
    ,['Проверьте подключение и попробуйте ещё раз.','Check your connection and try again.','请检查网络连接后重试。','Prüfe deine Verbindung und versuche es erneut.','Comprueba la conexión e inténtalo de nuevo.']
    ,['Очередь обработки','Processing queue','处理队列','Verarbeitungswarteschlange','Cola de procesamiento']
    ,['Лекция принята','Lecture queued','课程已加入队列','Vorlesung eingereiht','Clase en cola']
    ,['Обрабатываем лекцию','Processing lecture','正在处理课程','Vorlesung wird verarbeitet','Procesando la clase']
    ,['В очереди на обработку…','Waiting to be processed…','等待处理…','Wartet auf die Verarbeitung…','En cola para procesar…']
    ,['Прошло','Elapsed','已用时','Vergangen','Transcurrido']
    ,['примерно осталось','about','预计还需','noch etwa','aproximadamente quedan']
    ,['осталось','remaining','还剩','verbleibend','quedan']
    ,['завершаем текущий этап','finishing this step','正在完成当前步骤','aktueller Schritt wird abgeschlossen','terminando esta etapa']
    ,['Не удалось перевести содержание лекции. Нажмите, чтобы повторить.','Could not translate the lecture notes. Click to retry.','无法翻译课程内容。点击重试。','Der Vorlesungsinhalt konnte nicht übersetzt werden. Zum Wiederholen klicken.','No se pudo traducir el contenido de la clase. Haz clic para reintentar.']
    ,['Перевод продолжается в фоне. Откройте лекцию позже.','Translation is continuing in the background. Reopen the lecture later.','翻译正在后台继续。请稍后重新打开课程。','Die Übersetzung läuft im Hintergrund weiter. Öffne die Vorlesung später erneut.','La traducción continúa en segundo plano. Vuelve a abrir la clase más tarde.']
    ,['Не удалось обновить пересказ и главы. Нажмите, чтобы повторить.','Could not refresh the summary and chapters. Click to retry.','无法更新摘要和章节。点击重试。','Zusammenfassung und Kapitel konnten nicht aktualisiert werden. Zum Wiederholen klicken.','No se pudo actualizar el resumen y los capítulos. Haz clic para reintentar.']
    ,['Пересчёт продолжается в фоне. Откройте лекцию позже.','The update is continuing in the background. Reopen the lecture later.','更新正在后台继续。请稍后重新打开课程。','Die Aktualisierung läuft im Hintergrund weiter. Öffne die Vorlesung später erneut.','La actualización continúa en segundo plano. Vuelve a abrir la clase más tarde.']
    ,['Разделы появятся после обработки.','Chapters will appear after processing.','处理后将显示章节。','Kapitel erscheinen nach der Verarbeitung.','Los capítulos aparecerán al terminar el procesamiento.']
    ,['Конспект появится после обработки.','A summary will appear after processing.','处理后将显示摘要。','Eine Zusammenfassung erscheint nach der Verarbeitung.','El resumen aparecerá al terminar el procesamiento.']
    ,['Автоопределение языка','Automatic language detection','自动检测语言','Automatische Spracherkennung','Detección automática del idioma']
    ,['🌐 Автоопределение языка','🌐 Automatic language detection','🌐 自动检测语言','🌐 Sprache automatisch erkennen','🌐 Detección automática del idioma']
    ,['По умолчанию язык определяется по речи в видео. Интерфейс настраивается отдельно.','The video language is detected automatically by default. The interface language is set separately.','默认会自动识别视频语言。界面语言可单独设置。','Die Videosprache wird standardmäßig automatisch erkannt. Die Oberflächensprache wird separat eingestellt.','El idioma del vídeo se detecta automáticamente. El idioma de la interfaz se configura por separado.']
  ];
  locales.it={
  "Язык интерфейса": "Lingua dell’interfaccia",
  "ЗНАНИЯ — НАЙДЕНЫ": "IL SAPERE — RITROVATO",
  "В каждой лекции": "In ogni lezione",
  "есть ": "c’è ",
  "ответ.": "una risposta.",
  "Ищите идеи и объяснения, а не отдельные слова.": "Cerca idee e spiegazioni, non solo singole parole.",
  "Мы покажем нужный момент и поможем разобраться.": "Troveremo il momento giusto e ti aiuteremo a capire.",
  "Нажмите на лупу,": "Fai clic sulla lente",
  "чтобы найти идею": "per trovare un’idea",
  "идея найдена": "idea trovata",
  "СЕМАНТИЧЕСКИЙ ПОИСК": "RICERCA SEMANTICA",
  "Ищет по всем готовым лекциям": "Cerca in tutte le lezioni elaborate",
  "Найти": "Cerca",
  "ВАША БИБЛИОТЕКА": "LA TUA BIBLIOTECA",
  "Лекции ": "Lezioni ",
  "Добавить лекцию": "Aggiungi lezione",
  "Начните с первой лекции": "Inizia dalla tua prima lezione",
  "Загрузите видео — мы подготовим транскрипт, главы и смысловой поиск.": "Carica un video: prepareremo trascrizione, capitoli e ricerca semantica.",
  "ЛИЦЕНЗИЯ И УСЛОВИЯ ИСПОЛЬЗОВАНИЯ": "LICENZA E CONDIZIONI D’USO",
  "Язык речи в видео": "Lingua parlata nel video",
  "Выберите язык, на котором говорят в видео. Язык интерфейса меняется отдельно.": "Scegli la lingua parlata nel video. La lingua dell’interfaccia si imposta separatamente.",
  "Название лекции": "Titolo della lezione",
  "Папка для лекции": "Cartella della lezione",
  "＋ Новая папка": "＋ Nuova cartella",
  "Без папки (основная библиотека)": "Senza cartella (biblioteca principale)",
  "Отмена": "Annulla",
  "Создастся новая папка, и файл сразу будет перемещён в неё.": "Verrà creata una nuova cartella e il file sarà spostato al suo interno.",
  "Перетащите видео сюда": "Trascina qui il video",
  "или ": "oppure ",
  "выберите файл": "scegli un file",
  "Ссылка": "Link",
  "Файл видео": "File video",
  "Ссылка на видео": "Link del video",
  "Качество видео": "Qualità del video",
  "Лучшее доступное": "La migliore disponibile",
  "Начать обработку ": "Avvia elaborazione ",
  "Отменить загрузку": "Annulla caricamento",
  "Личный кабинет": "Il mio account",
  "ЛИЧНОЕ ПРОСТРАНСТВО": "IL TUO SPAZIO",
  "С возвращением": "Bentornato",
  "Войдите, чтобы открыть свою библиотеку лекций.": "Accedi per aprire la tua biblioteca di lezioni.",
  "Войти": "Accedi",
  "Создать аккаунт": "Crea account",
  "Логин": "Nome utente",
  "Пароль": "Password",
  "Введите логин и пароль вашего кабинета.": "Inserisci nome utente e password del tuo account.",
  "ВАШ АККАУНТ": "IL TUO ACCOUNT",
  "Свои буквы": "Le tue iniziali",
  "Сохранить": "Salva",
  "Загрузить своё фото": "Carica la tua foto",
  "лекций": "lezioni",
  "готово": "pronte",
  "Изменить пароль": "Cambia password",
  "Выйти из аккаунта ": "Esci dall’account ",
  "ПЕРЕМЕСТИТЬ ЛЕКЦИЮ": "SPOSTA LEZIONE",
  "Переместить лекцию": "Sposta lezione",
  "Выберите папку или создайте новую.": "Scegli una cartella o creane una nuova.",
  "Или создать новую папку": "Oppure crea una nuova cartella",
  "Создать и переместить ": "Crea e sposta ",
  "Оглавление": "Indice",
  "Краткий пересказ": "Riassunto",
  "Обновить пересказ и главы": "Aggiorna riassunto e capitoli",
  "Перераспознать речь": "Trascrivi di nuovo",
  "Транскрипт": "Trascrizione",
  "Главы": "Capitoli",
  "Удалить лекцию": "Elimina lezione",
  "Администрирование": "Amministrazione",
  "Аккаунты": "Account",
  "Видео на сервере": "Video sul server",
  "Настройки": "Impostazioni",
  "Создать папку": "Crea cartella",
  "Новая папка": "Nuova cartella",
  "Собрать лекции вместе": "Raggruppa le lezioni",
  "Дайте папке короткое название. Лекции можно будет перемещать из карточки каждой записи.": "Assegna un nome breve alla cartella. Potrai spostarvi le lezioni dalla scheda di ciascuna lezione.",
  "Название папки": "Nome della cartella",
  "Создать папку ": "Crea cartella ",
  "Папки с лекциями": "Cartelle delle lezioni",
  "БИБЛИОТЕКА": "BIBLIOTECA",
  "Все лекции": "Tutte le lezioni",
  "Свернуть меню": "Comprimi menu",
  "Развернуть меню": "Espandi menu",
  "Как устроен проект": "Come funziona il progetto",
  "Например, Введение в машинное обучение": "Ad esempio: Introduzione all’apprendimento automatico",
  "Поддерживаются YouTube, VK Видео, Rutube и многие платформы yt-dlp. Доступные разрешения зависят от ролика.": "Sono supportati YouTube, VK Video, Rutube e molte piattaforme di yt-dlp. Le risoluzioni disponibili dipendono dal video.",
  "Переместить в папку": "Sposta nella cartella",
  "С начала": "Dall’inizio",
  "ГОТОВА": "PRONTA",
  "ОШИБКА": "ERRORE",
  "ОБРАБОТКА": "IN ELABORAZIONE",
  "ГОТОВИТСЯ": "IN CODA",
  "лучшее доступное": "la migliore disponibile",
  "Краткий конспект": "Appunti brevi",
  "Загружаем транскрипт…": "Caricamento della trascrizione…",
  "Разделы появятся после обработки.": "I capitoli appariranno al termine dell’elaborazione.",
  "Разделы не найдены.": "Nessun capitolo trovato.",
  "Составляем…": "Creazione in corso…",
  "Готово": "Fatto",
  "Сохраняем…": "Salvataggio…",
  "Аватар сохранён": "Avatar salvato",
  "Лекция не найдена": "Lezione non trovata",
  "Лекция по ссылке": "Lezione da un link",
  "Загрузка модели распознавания": "Caricamento del modello vocale",
  "НОВАЯ ЛЕКЦИЯ": "NUOVA LEZIONE",
  "Загрузите видео или вставьте ссылку — остальное мы сделаем сами.": "Carica un video o incolla un link: al resto pensiamo noi.",
  "· MP4, WebM · до 500 МБ": "· MP4, WebM · fino a 500 MB",
  "До 2160p · 4K": "Fino a 2160p · 4K",
  "До 1440p": "Fino a 1440p",
  "До 1080p · Full HD": "Fino a 1080p · Full HD",
  "До 720p · HD": "Fino a 720p · HD",
  "До 480p": "Fino a 480p",
  "До 360p": "Fino a 360p",
  "НОВАЯ ПАПКА": "NUOVA CARTELLA",
  "У каждой учётной записи своя библиотека. Содержимое хранится в зашифрованном виде.": "Ogni account ha la propria biblioteca. I contenuti vengono conservati in forma cifrata.",
  "Используя Лекторий, вы принимаете": "Utilizzando Lectorium, accetti le",
  "условия использования": "condizioni d’uso",
  "Пользователь": "Utente",
  "Личная библиотека лекций": "Biblioteca personale di lezioni",
  "БЕЗОПАСНОСТЬ": "SICUREZZA",
  "Новый пароль": "Nuova password",
  "Подтвердите текущий пароль и задайте новый.": "Conferma la password attuale e impostane una nuova.",
  "Текущий пароль": "Password attuale",
  "Сохранить пароль": "Salva password",
  "ДОСТУП К АККАУНТУ": "ACCESSO ALL’ACCOUNT",
  "Задать новый пароль": "Imposta una nuova password",
  "УПРАВЛЕНИЕ СИСТЕМОЙ": "GESTIONE DEL SISTEMA",
  "Загружаем данные…": "Caricamento dei dati…",
  "Авто": "Auto",
  "Светлая": "Chiaro",
  "Тёмная": "Scuro",
  "Сменить тему сайта": "Cambia tema del sito",
  "Сменить тему сайта: автоматически": "Cambia tema del sito: automatico",
  "Сменить тему сайта: светлая": "Cambia tema del sito: chiaro",
  "Сменить тему сайта: тёмная": "Cambia tema del sito: scuro",
  "Перевести субтитры": "Traduci sottotitoli",
  "Переводим субтитры…": "Traduzione dei sottotitoli…",
  "Субтитры переведены": "Sottotitoli tradotti",
  "Не удалось перевести субтитры": "Impossibile tradurre i sottotitoli",
  "Не удалось перевести эту часть лекции. Повторите попытку.": "Impossibile tradurre questa parte della lezione. Riprova.",
  "Перевод занял слишком много времени. Повторите попытку.": "La traduzione ha richiesto troppo tempo. Riprova.",
  "Язык перевода": "Lingua della traduzione",
  "Перевод": "Traduzione",
  "Автоматически": "Automatico",
  "ЛОКАЛЬНАЯ ДЕМОНСТРАЦИЯ · РАБОТАЕТ БЕЗ ИНТЕРНЕТА": "DEMO LOCALE · FUNZIONA SENZA INTERNET",
  "Офлайн-стенд": "Demo offline",
  "Данные примера в комплекте": "Dati di esempio inclusi",
  "Философия": "Filosofia",
  "Открыть лекцию": "Apri lezione",
  "Демо показывает, как устроен путь от видео до знаний.": "La demo mostra il percorso dal video alla conoscenza.",
  "ЛОКАЛЬНЫЙ ПОИСК ПО ТЕКСТУ": "RICERCA LOCALE NEL TESTO",
  "Например: как Кант объясняет опыт?": "Ad esempio: come spiega Kant l’esperienza?",
  "Примеры: Кант · опыт · время": "Esempi: Kant · esperienza · tempo",
  "ПРИМЕР ДЛЯ ПОКАЗА": "ESEMPIO DIMOSTRATIVO",
  "ЧТО ПРОИСХОДИТ": "COSA SUCCEDE",
  "От видео — к понятным моментам": "Dal video ai passaggi chiari",
  "Загрузка": "Caricamento",
  "Распознавание": "Riconoscimento vocale",
  "Навигация": "Navigazione",
  "В рабочей версии добавляют видеофайл или ссылку на видео.": "Nella versione online si aggiunge un file video o un link.",
  "Для русской речи используется GigaAM-v3; английская, китайская, немецкая и испанская распознаются мультиязычной моделью. Язык можно определить автоматически, расшифровка сохраняет таймкоды.": "Per il russo si usa GigaAM-v3; le altre lingue sono riconosciute da un modello multilingue. La lingua può essere rilevata automaticamente e la trascrizione conserva i riferimenti temporali.",
  "Транскрипт, тематические главы и смысловой поиск помогают быстро найти нужный эпизод.": "Trascrizione, capitoli tematici e ricerca semantica aiutano a trovare rapidamente il passaggio desiderato.",
  "В этой офлайн-демонстрации загрузка выключена. Обработка видео доступна в основной версии на сервере.": "Il caricamento è disattivato in questa demo offline. L’elaborazione dei video è disponibile nella versione sul server.",
  "В этой папке нет лекций.": "Questa cartella non contiene lezioni.",
  "Перевод субтитров требует серверной модели и доступен в основной версии сайта.": "La traduzione dei sottotitoli richiede il modello sul server ed è disponibile nella versione online.",
  "Аватар": "Avatar",
  "Без папки": "Senza cartella",
  "Проверьте подключение и попробуйте ещё раз.": "Controlla la connessione e riprova.",
  "Очередь обработки": "Coda di elaborazione",
  "Лекция принята": "Lezione in coda",
  "Обрабатываем лекцию": "Elaborazione della lezione",
  "Конспект появится после обработки.": "Il riassunto apparirà al termine dell’elaborazione.",
  "Автоопределение языка": "Rilevamento automatico della lingua",
  "🌐 Автоопределение языка": "Rilevamento automatico della lingua",
  "По умолчанию язык определяется по речи в видео. Интерфейс настраивается отдельно.": "La lingua del video viene rilevata automaticamente. La lingua dell’interfaccia si imposta separatamente.",
  "Закрыть": "Chiudi",
  "Действия": "Azioni",
  "Меню лекции": "Menu della lezione",
  "Найти идею в лекциях": "Trova un’idea nelle lezioni",
  "Например: как работает градиентный спуск?": "Ad esempio: come funziona la discesa del gradiente?",
  "Повторить обработку": "Riprova elaborazione",
  "Нажмите, чтобы увидеть ошибку": "Fai clic per vedere l’errore",
  "Не удалось обработать речь": "Impossibile elaborare il parlato",
  "Отменить обработку": "Annulla elaborazione",
  "ОТМЕНЕНА": "ANNULLATA",
  "Обработка отменена": "Elaborazione annullata",
  "Войти через": "Accedi con",
  "Скачать видео": "Scarica video",
  "Итальянский": "Italiano",
  "Переместить лекцию в папку": "Sposta la lezione nella cartella",
  "Все записи": "Tutte le registrazioni",
  "Профиль пользователя": "Profilo utente",
  "Роль": "Ruolo",
  "Администратор": "Amministratore",
  "Дата регистрации": "Data di registrazione",
  "Просмотреть профиль": "Visualizza profilo",
  "Сохранить настройки": "Salva impostazioni",
  "Проверить прокси": "Verifica proxy",
  "Пользователи": "Utenti",
  "Создайте аккаунт": "Crea un account",
  "Создайте личное пространство для своих лекций.": "Crea uno spazio personale per le tue lezioni.",
  "Создать кабинет": "Crea account"
};
  Object.assign(locales.it,{"Открыть лекцию ↗": "Apri lezione ↗", "ДЕМО · 23 МИН": "DEMO · 23 MIN", "Перейти к поиску": "Vai alla ricerca", "23:24 · 4 главы · русский язык": "23:24 · 4 capitoli · lingua russa", "Русская речь распознаётся GigaAM-v3; английская, китайская, немецкая и испанская — мультиязычной моделью. Язык ролика можно определить автоматически. Расшифровка сохраняется с таймкодами.": "Il russo viene riconosciuto da GigaAM-v3; inglese, cinese, tedesco, spagnolo e italiano da Whisper. La lingua può essere rilevata automaticamente. La trascrizione conserva i riferimenti temporali.", 'В очереди на обработку…':'In attesa di elaborazione…','Прошло':'Trascorso','примерно осталось':'mancano circa','осталось':'mancano','завершаем текущий этап':'completamento della fase corrente','Не удалось перевести содержание лекции. Нажмите, чтобы повторить.':'Impossibile tradurre il contenuto della lezione. Fai clic per riprovare.','Перевод продолжается в фоне. Откройте лекцию позже.':'La traduzione continua in background. Riapri la lezione più tardi.','Не удалось обновить пересказ и главы. Нажмите, чтобы повторить.':'Impossibile aggiornare il riepilogo e i capitoli. Fai clic per riprovare.','Пересчёт продолжается в фоне. Откройте лекцию позже.':'L’aggiornamento continua in background. Riapri la lezione più tardi.'});
  const localesOrder=['ru','en','zh','de','es'];
  for(const row of extraRows)for(let index=0;index<localesOrder.length;index++)if(localesOrder[index])locales[localesOrder[index]][row[0]]=row[index];
  for(const locale of Object.keys(locales))locales[locale]=Object.fromEntries(Object.entries(locales[locale]).map(([key,value])=>[normalize(key),value]));
  const pageTitles=document.querySelector('.offline-banner')
    ?{ru:'Лекторий — локальная демонстрация',en:'Lectorium — offline demo',zh:'Lectorium — 离线演示',de:'Lectorium — Offline-Demo',es:'Lectorium — demo sin conexión',it:'Lectorium — demo offline'}
    :{ru:'Лекторий — поиск по смыслу',en:'Lectorium — semantic lecture search',zh:'Lectorium — 课程语义搜索',de:'Lectorium — semantische Vorlesungssuche',es:'Lectorium — búsqueda semántica en clases',it:'Lectorium — ricerca semantica nelle lezioni'};
  const playerLabels={
    ru:['С начала','Назад на {seektime} сек.','Воспроизвести','Пауза','Вперёд на {seektime} сек.','Перемотка','{currentTime} из {duration}','Просмотрено','Загружено','Текущее время','Длительность','Громкость','Выключить звук','Включить звук','Скачать видео','На весь экран','Выйти из полноэкранного режима','Видеоплеер: {title}','Субтитры','Настройки','Картинка в картинке','Назад','Скорость','Обычная','Качество','Повтор','Начало','Конец','Все','Сбросить','Выключено','Включено','Реклама'],
    en:['Restart','Rewind {seektime} seconds','Play','Pause','Forward {seektime} seconds','Seek','{currentTime} of {duration}','Played','Buffered','Current time','Duration','Volume','Mute','Unmute','Download video','Enter fullscreen','Exit fullscreen','Video player: {title}','Captions','Settings','Picture in picture','Back','Speed','Normal','Quality','Loop','Start','End','All','Reset','Disabled','Enabled','Advertisement'],
    zh:['重新开始','后退 {seektime} 秒','播放','暂停','快进 {seektime} 秒','定位','{currentTime} / {duration}','已播放','已缓冲','当前时间','时长','音量','静音','取消静音','下载视频','进入全屏','退出全屏','视频播放器：{title}','字幕','设置','画中画','返回','速度','正常','画质','循环','开始','结束','全部','重置','关闭','开启','广告'],
    de:['Neustart','{seektime} Sekunden zurück','Abspielen','Pause','{seektime} Sekunden vor','Suchen','{currentTime} von {duration}','Abgespielt','Gepuffert','Aktuelle Zeit','Dauer','Lautstärke','Stumm','Ton an','Video herunterladen','Vollbild öffnen','Vollbild verlassen','Videoplayer: {title}','Untertitel','Einstellungen','Bild im Bild','Zurück','Geschwindigkeit','Normal','Qualität','Wiederholen','Start','Ende','Alle','Zurücksetzen','Deaktiviert','Aktiviert','Werbung'],
    es:['Reiniciar','Retroceder {seektime} s','Reproducir','Pausa','Avanzar {seektime} s','Buscar','{currentTime} de {duration}','Reproducido','Cargado','Tiempo actual','Duración','Volumen','Silenciar','Activar sonido','Descargar vídeo','Entrar en pantalla completa','Salir de pantalla completa','Reproductor de vídeo: {title}','Subtítulos','Ajustes','Imagen en imagen','Volver','Velocidad','Normal','Calidad','Repetir','Inicio','Fin','Todos','Restablecer','Desactivado','Activado','Anuncio']
  };
  playerLabels.it=["Ricomincia", "Indietro di {seektime} secondi", "Riproduci", "Pausa", "Avanti di {seektime} secondi", "Cerca", "{currentTime} di {duration}", "Riprodotto", "Caricato", "Tempo attuale", "Durata", "Volume", "Disattiva audio", "Attiva audio", "Scarica video", "Schermo intero", "Esci da schermo intero", "Lettore video: {title}", "Sottotitoli", "Impostazioni", "Picture in picture", "Indietro", "Velocità", "Normale", "Qualità", "Ripeti", "Inizio", "Fine", "Tutti", "Reimposta", "Disattivato", "Attivato", "Pubblicità"];
  const playerKeys=['restart','rewind','play','pause','fastForward','seek','seekLabel','played','buffered','currentTime','duration','volume','mute','unmute','download','enterFullscreen','exitFullscreen','frameTitle','captions','settings','pip','menuBack','speed','normal','quality','loop','start','end','all','reset','disabled','enabled','advertisement'];
  window.getPlayerTranslations=locale=>Object.fromEntries(playerKeys.map((key,index)=>[key,playerLabels[locale]?.[index]||playerLabels.ru[index]]));
  const originalText = new WeakMap(), lastWrittenText = new WeakMap(), originalAttrs = new WeakMap(), lastWrittenAttrs = new WeakMap(), textNodes = new Set(), attrNodes = new Set();
  let language = 'ru', writing = false;
  const tr = (source, locale=language) => locales[locale]?.[normalize(source)] ?? source;
  function translateText(node, force=false){
    const current=node.nodeValue||''; if(!current.trim()||current.length>100000)return;
    let source=originalText.get(node);
    if(source===undefined){ source=current; originalText.set(node,source); textNodes.add(node); }
    else if(!force&&current===lastWrittenText.get(node))return;
    else if(!force&&current!==source){ source=current; originalText.set(node,source); }
    const translated=tr(source);
    const leading=source.match(/^\s*/)?.[0]||'', trailing=source.match(/\s*$/)?.[0]||'';
    const value=`${leading}${translated}${trailing}`;
    lastWrittenText.set(node,value);
    if(node.nodeValue!==value)node.nodeValue=value;
  }
  const translatedAttributes=new Set(['placeholder','title','aria-label']);
  function translateAttrs(el, force=false){
    let state=originalAttrs.get(el); if(!state){state=new Map();originalAttrs.set(el,state)}
    let lastState=lastWrittenAttrs.get(el);if(!lastState){lastState=new Map();lastWrittenAttrs.set(el,lastState)}
    for(const name of translatedAttributes){
      if(!el.hasAttribute(name))continue;
      const current=el.getAttribute(name); let source=state.get(name);
      if(source===undefined){source=current;state.set(name,source);attrNodes.add(el)}
      else if(!force&&current===lastState.get(name))continue;
      else if(!force&&current!==source){source=current;state.set(name,source)}
      const value=tr(source);lastState.set(name,value);if(current!==value)el.setAttribute(name,value);
    }
  }
  function visit(root){
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(node){return node.parentElement?.closest('script,style,[data-no-translate],.transcript-line,.summary-text,.chapter-title,.lecture-card h3,#detailTitle')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}});
    let node;while(node=walker.nextNode())translateText(node);
    if(root.nodeType===1){translateAttrs(root);root.querySelectorAll('*').forEach(translateAttrs)}
  }
  function setLanguage(locale,reloadAfterChange=false){
    const previousLanguage=language;
    if(!locales[locale])locale='ru'; language=locale; document.documentElement.lang=locale;
    try{localStorage.setItem('lectoriumLanguage',locale)}catch{}
    const picker=document.querySelector('#siteLanguage');if(picker)picker.value=locale;
    writing=true;
    for(const node of [...textNodes])if(node.isConnected)translateText(node,true);
    for(const el of [...attrNodes])if(el.isConnected)translateAttrs(el,true);
    visit(document.body);
    document.title=pageTitles[locale];
    const headline=document.querySelector('#heroHeadline');
    if(headline)headline.innerHTML={ru:'В каждой лекции<br>есть <em>ответ.</em>',en:'Every lecture has<br>an <em>answer.</em>',zh:'每堂课中<br>都有<em>答案。</em>',de:'In jeder Vorlesung<br>steckt eine <em>Antwort.</em>',es:'Cada clase tiene<br>una <em>respuesta.</em>',it:'In ogni lezione<br>c’è <em>una risposta.</em>'}[locale];
    writing=false;
    window.dispatchEvent(new CustomEvent('lectorium:language-change',{detail:{locale}}));
    if(reloadAfterChange&&previousLanguage!==locale){
      const resume=window.getLectureResumeState?.();
      if(resume)try{sessionStorage.setItem('lectoriumResumeLecture',JSON.stringify(resume))}catch{}
      window.location.reload();
    }
  }
  const picker=document.querySelector('#siteLanguage');
  let saved='ru';try{saved=localStorage.getItem('lectoriumLanguage')||'ru'}catch{}
  if(picker)picker.addEventListener('change',()=>setLanguage(picker.value,true));
  window.t=tr; window.getUiLanguage=()=>language; window.setUiLanguage=setLanguage;
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setLanguage(saved),{once:true});else setLanguage(saved);
  const observer=new MutationObserver(records=>{
    if(writing)return;
    writing=true;
    for(const record of records){
      if(record.type==='characterData')translateText(record.target);
      else if(record.type==='attributes')translateAttrs(record.target);
      else for(const node of record.addedNodes)if(node.nodeType===1)visit(node);else if(node.nodeType===3)translateText(node);
    }
    writing=false;
  });
  observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','title','aria-label']});
})();
