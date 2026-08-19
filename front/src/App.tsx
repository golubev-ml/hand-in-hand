import { useState, useEffect, useRef } from 'react'

// ─── Types ───────────────────────────────────────────────────────────────────

type ArtCategory = 'drawing' | 'painting' | 'digital'
type FilterCategory = 'all' | ArtCategory | 'new'
type SortKey = 'popular' | 'price-asc' | 'price-desc' | 'newest'
type CheckoutStep = 'form' | 'payment' | 'success'

interface Artwork {
  id: number
  title: string
  author: string
  age: number
  category: ArtCategory
  price: number
  description: string
  img: string
  isNew: boolean
  isFeatured: boolean
  story: string
  popularity: number
  status?: string
  minPrice?: number
}

interface CartItem {
  artwork: Artwork
  qty: number
}

// ─── Data ────────────────────────────────────────────────────────────────────

const ARTWORKS: Artwork[] = [
  {
    id: 1,
    title: 'Весенний лес',
    author: 'Маша К.',
    age: 8,
    category: 'painting',
    price: 2500,
    description: 'Акварельный пейзаж с яркими весенними красками. Маша передала настроение первых тёплых дней через нежные переходы зелёного и голубого.',
    img: 'https://images.unsplash.com/photo-1560421683-6856ea585c78?w=700&h=560&fit=crop&auto=format',
    isNew: true,
    isFeatured: true,
    story: 'Маша нарисовала этот лес после прогулки с мамой в парке. Она сказала: «Я хочу, чтобы люди тоже почувствовали этот запах травы».',
    popularity: 95,
  },
  {
    id: 2,
    title: 'Мой дом',
    author: 'Артём С.',
    age: 7,
    category: 'drawing',
    price: 1800,
    description: 'Простой и трогательный рисунок цветными карандашами. Дом, семья и солнце — главное, что важно в жизни.',
    img: 'https://images.unsplash.com/photo-1573020568125-d15af9c3e777?w=700&h=560&fit=crop&auto=format',
    isNew: false,
    isFeatured: true,
    story: 'Артём из небольшого городка в Ярославской области. Это его первый рисунок, который он решился показать другим людям. Участие в выставке изменило его.',
    popularity: 88,
  },
  {
    id: 3,
    title: 'Город будущего',
    author: 'Дима Р.',
    age: 12,
    category: 'digital',
    price: 3500,
    description: 'Цифровая иллюстрация с детальным изображением фантастического города с летающими машинами и зелёными башнями.',
    img: 'https://images.unsplash.com/photo-1597863881769-8d8ff8ab8b2a?w=700&h=560&fit=crop&auto=format',
    isNew: true,
    isFeatured: true,
    story: 'Дима хочет стать архитектором. Он несколько месяцев учился рисовать на планшете и создал этот удивительный мир из нуля.',
    popularity: 92,
  },
  {
    id: 4,
    title: 'Бабочка в саду',
    author: 'Аня Л.',
    age: 9,
    category: 'painting',
    price: 2200,
    description: 'Гуашь на картоне. Яркая бабочка среди цветов — воплощение детской радости и свободы.',
    img: 'https://images.unsplash.com/photo-1666710988451-ba4450498967?w=700&h=560&fit=crop&auto=format',
    isNew: false,
    isFeatured: false,
    story: 'Аня увлекается энтомологией. Она знает названия сотен бабочек и мечтает нарисовать их всех.',
    popularity: 75,
  },
  {
    id: 5,
    title: 'Зимний вечер',
    author: 'Лена В.',
    age: 11,
    category: 'painting',
    price: 3000,
    description: 'Пастель на тонированной бумаге. Тихий зимний вечер, фонари и следы на снегу.',
    img: 'https://images.unsplash.com/photo-1510832842230-87253f48d74f?w=700&h=560&fit=crop&auto=format',
    isNew: true,
    isFeatured: false,
    story: 'Лена живёт в маленьком городке в Сибири. Снег для неё — это тишина и покой, которые она передаёт в своих работах.',
    popularity: 81,
  },
  {
    id: 6,
    title: 'Радужный конь',
    author: 'Миша Ф.',
    age: 6,
    category: 'drawing',
    price: 1500,
    description: 'Фломастеры на бумаге. Самый радостный конь на свете, нарисованный самым весёлым автором.',
    img: 'https://images.unsplash.com/photo-1614712201488-9942af86b87b?w=700&h=560&fit=crop&auto=format',
    isNew: false,
    isFeatured: false,
    story: 'Миша — самый младший участник нашей программы. Он рисует каждый день и хочет стать художником, «как Ван Гог».',
    popularity: 70,
  },
  {
    id: 7,
    title: 'Портрет бабушки',
    author: 'Катя Н.',
    age: 10,
    category: 'drawing',
    price: 2800,
    description: 'Простой карандаш, сложное чувство. Катя нарисовала портрет бабушки с такой нежностью, что он выглядит как настоящее произведение искусства.',
    img: 'https://images.unsplash.com/photo-1597116868150-099875391584?w=700&h=560&fit=crop&auto=format',
    isNew: false,
    isFeatured: false,
    story: 'Катя говорит, что бабушка — её самый важный человек. «Я хочу, чтобы она видела себя такой, какой вижу её я».',
    popularity: 90,
  },
  {
    id: 8,
    title: 'Океан мечты',
    author: 'Саша П.',
    age: 13,
    category: 'digital',
    price: 4200,
    description: 'Цифровая живопись с глубоким синим морем, светящимися медузами и загадочными глубинами.',
    img: 'https://images.unsplash.com/photo-1536221993589-9edbbca2c7fc?w=700&h=560&fit=crop&auto=format',
    isNew: true,
    isFeatured: false,
    story: 'Саша никогда не видел моря. Он создаёт его из фантазии и книг — и оно получается невероятным.',
    popularity: 86,
  },
]

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(p: number) {
  return p.toLocaleString('ru-RU') + ' ₽'
}

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

const FOOTER_INFO: Record<string, string[]> = {
  'О нас': ['Фонд «Искусство чтобы жить» основан в 2012 году группой педагогов и художников. Мы помогаем детям из малообеспеченных семей, сиротам и детям с особенностями развития находить себя через творчество.', 'Раздел наполняется командой фонда.'],
  'Наши проекты': ['Студии рисунка в восьми городах России, бесплатные материалы и занятия для всех детей.', 'Раздел наполняется командой фонда.'],
  'Отчёты': ['Здесь будут публиковаться годовые отчёты фонда: финансы, программы, результаты.', 'Раздел наполняется командой фонда.'],
  'Партнёры': ['Мы сотрудничаем с галереями, школами искусства и компаниями, которые поддерживают детское творчество.', 'Раздел наполняется командой фонда.'],
  'Все работы': ['Полная галерея работ наших студий: живопись, рисунки и цифровое искусство.', 'Раздел наполняется командой фонда.'],
  'Живопись': ['Подборка живописных работ студентов.', 'Раздел наполняется командой фонда.'],
  'Рисунки': ['Подборка графических работ студентов.', 'Раздел наполняется командой фонда.'],
  'Цифровое искусство': ['Подборка работ, созданных в цифровых техниках.', 'Раздел наполняется командой фонда.'],
  'Пожертвовать': ['Ваше пожертвование идёт на материалы, занятия и выставки для детей. 30% с каждой продажи также возвращается в фонд.', 'Раздел наполняется командой фонда.'],
  'Купить работу': ['Покупая работу, вы поддерживаете ребёнка-автора и фонд. Оформление заказа занимает пару минут.', 'Раздел наполняется командой фонда.'],
  'Стать волонтёром': ['Мы ищем волонтёров для занятий, выставок и организации мероприятий.', 'Раздел наполняется командой фонда.'],
  'Корпоративное партнёрство': ['Программы для компаний: благотворительные выставки, закупка работ, волонтёрские дни.', 'Раздел наполняется командой фонда.'],
}

const CATEGORY_LABELS: Record<FilterCategory, string> = {
  all: 'Все работы',
  drawing: 'Рисунки',
  painting: 'Живопись',
  digital: 'Цифровое',
  new: 'Новинки',
}

const SORT_LABELS: Record<SortKey, string> = {
  popular: 'По популярности',
  'price-asc': 'Сначала дешевле',
  'price-desc': 'Сначала дороже',
  newest: 'Новые',
}

// ─── ArtworkCard ─────────────────────────────────────────────────────────────

function ArtworkCard({
  artwork,
  onView,
  onAdd,
  onBuy,
  inCart,
}: {
  artwork: Artwork
  onView: () => void
  onAdd: () => void
  onBuy: (artwork: Artwork, price: number) => void
  inCart: boolean
}) {
  const [added, setAdded] = useState(false)
  const [imgLoaded, setImgLoaded] = useState(false)

  function handleAdd(e: React.MouseEvent) {
    e.stopPropagation()
    onAdd()
    setAdded(true)
    setTimeout(() => setAdded(false), 1800)
  }

  const catColors: Record<ArtCategory, string> = {
    drawing: 'bg-[#EBF4FA] text-[#4A7C9E]',
    painting: 'bg-[#E8F2EB] text-[#3D7A52]',
    digital: 'bg-[#F5EFE3] text-[#8B6F3E]',
  }
  const catNames: Record<ArtCategory, string> = {
    drawing: 'Рисунок',
    painting: 'Живопись',
    digital: 'Цифровое',
  }

  const isSold = artwork.status === 'sold'
  
  return (
    <div
      onClick={onView}
      className={`group bg-[#FFFCF7] rounded-2xl overflow-hidden border border-[#E8DCC8] transition-all duration-300 hover:shadow-lg hover:-translate-y-1 ${isSold ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'}`}
    >
      <div className="relative overflow-hidden bg-[#F5EFE3]" style={{ aspectRatio: '4/3' }}>
        {!imgLoaded && (
          <div className="absolute inset-0 bg-[#F0E8D8] animate-pulse" />
        )}
        <img
          src={artwork.img}
          alt={`"${artwork.title}" — работа ${artwork.author}`}
          className={`w-full h-full object-cover transition-transform duration-500 group-hover:scale-105 ${imgLoaded ? 'opacity-100' : 'opacity-0'}`}
          onLoad={() => setImgLoaded(true)}
        />
        {artwork.isNew && (
          <span className="absolute top-3 left-3 bg-[#E07A5F] text-white text-xs font-bold px-2.5 py-1 rounded-full">
            Новинка
          </span>
        )}
        {isSold && (
          <>
            <div className="absolute inset-0 bg-black/20" />
            <span className="absolute top-3 right-3 bg-[#4A7C59] text-white px-3 py-1.5 rounded-full text-xs font-bold">Продано</span>
          </>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        {!isSold && (
          <button
            onClick={inCart ? () => onBuy(artwork, artwork.price) : handleAdd}
            className={`absolute bottom-3 right-3 text-sm font-semibold px-4 py-2 rounded-full transition-all duration-300 transform translate-y-2 opacity-0 group-hover:opacity-100 group-hover:translate-y-0 ${
              inCart
                ? 'bg-[#4A7C59] text-white'
                : added
                ? 'bg-[#4A7C59] text-white'
                : 'bg-white text-[#2C2416] hover:bg-[#4A7C59] hover:text-white'
            }`}
          >
            {inCart ? 'Перейти к оплате' : added ? '✓ Добавлено' : '+ В корзину'}
          </button>
        )}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className="font-serif text-lg text-[#2C2416] leading-tight">{artwork.title}</h3>
          <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${catColors[artwork.category]}`}>
            {catNames[artwork.category]}
          </span>
        </div>
        <p className="text-sm text-[#A89070] mb-3">
          {artwork.author}, {artwork.age} лет
        </p>
        <div className="flex items-center justify-between">
          <span className="text-[#4A7C59] font-bold text-lg">от {fmt(artwork.minPrice || 500)}</span>
          <span className="text-xs text-[#A89070]">30% — фонду</span>
        </div>
      </div>
    </div>
  )
}

// ─── ArtworkModal ─────────────────────────────────────────────────────────────

function ArtworkModal({
  artwork,
  onClose,
  onBuy,
}: {
  artwork: Artwork
  onClose: () => void
  onBuy: (artwork: Artwork, price: number) => void
}) {
  const isSold = artwork.status === 'sold'
  const [price, setPrice] = useState(artwork.minPrice || 500)

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  function handleBuy() {
    const finalPrice = Math.max(price, artwork.minPrice || 500)
    onBuy(artwork, finalPrice)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[#FFFCF7] rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="grid md:grid-cols-2">
          <div className="relative bg-[#F0E8D8]" style={{ minHeight: '320px' }}>
            <img
              src={artwork.img}
              alt={artwork.title}
              className="w-full h-full object-cover md:rounded-l-3xl"
            />
            <button
              onClick={onClose}
              className="absolute top-4 right-4 md:hidden bg-white/80 rounded-full w-9 h-9 flex items-center justify-center text-[#2C2416] hover:bg-white transition-colors"
            >
              ✕
            </button>
          </div>
          <div className="p-8 flex flex-col">
            <div className="flex items-start justify-between mb-1">
              <h2 className="font-serif text-2xl text-[#2C2416] leading-tight">{artwork.title}</h2>
              <button
                onClick={onClose}
                className="hidden md:flex shrink-0 text-[#A89070] hover:text-[#2C2416] w-8 h-8 items-center justify-center rounded-full hover:bg-[#F0E8D8] transition-colors"
              >
                ✕
              </button>
            </div>
            <p className="text-[#A89070] text-sm mb-4">
              Автор: <strong className="text-[#6B5B42]">{artwork.author}</strong>, {artwork.age} лет
            </p>
            <p className="text-[#4B3F30] text-sm leading-relaxed mb-4">{artwork.description}</p>

            <div className="bg-[#E8F2EB] rounded-xl p-4 mb-6">
              <p className="text-xs text-[#4A7C59] font-semibold mb-1 uppercase tracking-wide">История работы</p>
              <p className="text-sm text-[#2C2416] leading-relaxed italic">«{artwork.story}»</p>
            </div>

            <div className="bg-[#FBF0EC] rounded-xl p-3 mb-6 text-sm text-[#A05A3F]">
              🎨 <strong>30% от продажи</strong> идёт напрямую в фонд на поддержку юных художников
            </div>

            <div className="mt-auto">
              {isSold ? (
                <div className="bg-[#F5F0E8] rounded-xl p-4 text-center">
                  <p className="text-[#6B5B42] font-semibold">Эта картина уже продана</p>
                </div>
              ) : (
                <>
                  <div className="mb-4">
                    <label className="block text-xs text-[#A89070] mb-1">Ваша цена (от {fmt(artwork.minPrice || 500)})</label>
                    <input
                      type="number"
                      min={artwork.minPrice || 500}
                      step="50"
                      value={price}
                      onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                      onBlur={() => setPrice(Math.max(price, artwork.minPrice || 500))}
                      className="w-full border border-[#E8DCC8] rounded-lg px-3 py-2 text-lg font-bold text-[#4A7C59] focus:border-[#4A7C59] outline-none"
                      placeholder="Ваша цена"
                    />
                  </div>
                  <button
                    onClick={handleBuy}
                    className="w-full py-3.5 rounded-2xl font-bold text-base bg-[#2C2416] text-white hover:bg-[#4A7C59] transition-all duration-300"
                  >
                    Перейти к оплате
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── CartSidebar ──────────────────────────────────────────────────────────────

function CartSidebar({
  items,
  onClose,
  onRemove,
  onChangeQty,
  onCheckout,
}: {
  items: CartItem[]
  onClose: () => void
  onRemove: (id: number) => void
  onChangeQty: (id: number, qty: number) => void
  onCheckout: () => void
  onPriceChange: (id: number, price: number) => void
}) {
  const total = items.reduce((s, i) => s + i.artwork.price * i.qty, 0)

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#FFFCF7] w-full max-w-md h-full flex flex-col shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-[#E8DCC8]">
          <h2 className="font-serif text-xl text-[#2C2416]">
            Корзина {items.length > 0 && <span className="text-[#A89070] text-base">({items.length})</span>}
          </h2>
          <button
            onClick={onClose}
            className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-[#F0E8D8] text-[#6B5B42] transition-colors"
          >
            ✕
          </button>
        </div>

        {items.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="text-6xl mb-4">🎨</div>
            <p className="font-serif text-xl text-[#2C2416] mb-2">Корзина пуста</p>
            <p className="text-sm text-[#A89070]">Добавьте работы из галереи, чтобы поддержать юных художников</p>
            <button
              onClick={() => { onClose(); scrollTo('gallery') }}
              className="mt-6 bg-[#4A7C59] text-white px-6 py-3 rounded-2xl font-semibold hover:bg-[#3D6649] transition-colors"
            >
              Перейти в галерею
            </button>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {items.map(item => (
                <div key={item.artwork.id} className="flex gap-3 bg-white rounded-2xl p-3 border border-[#E8DCC8]">
                  <img
                    src={item.artwork.img}
                    alt={item.artwork.title}
                    className="w-16 h-16 rounded-xl object-cover bg-[#F0E8D8] shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-[#2C2416] truncate">{item.artwork.title}</p>
                    <p className="text-xs text-[#A89070] mb-2">{item.artwork.author}, {item.artwork.age} лет</p>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min={item.artwork.minPrice || 500}
                        step="50"
                        value={item.artwork.price}
                        onChange={(e) => onPriceChange(item.artwork.id, parseFloat(e.target.value) || 0)}
                        className="w-24 border border-[#E8DCC8] rounded-lg px-2 py-1 text-sm font-bold text-[#4A7C59] focus:border-[#4A7C59] outline-none"
                        placeholder="Ваша цена"
                      />
                      <span className="text-xs text-[#A89070]">₽ (от {fmt(item.artwork.minPrice || 500)})</span>
                    </div>
                  </div>
                  <button
                    onClick={() => onRemove(item.artwork.id)}
                    className="text-[#C8B89A] hover:text-[#E07A5F] transition-colors text-sm shrink-0"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>

            <div className="p-6 border-t border-[#E8DCC8]">
              <div className="flex items-center justify-between mb-4">
                <span className="text-[#6B5B42]">Итого</span>
                <span className="font-bold text-xl text-[#2C2416]">{fmt(total)}</span>
              </div>
              <div className="bg-[#E8F2EB] rounded-xl p-3 mb-4 text-xs text-[#4A7C59]">
                🎨 {fmt(Math.round(total * 0.3))} из вашего заказа поддержат юных художников фонда
              </div>
              <button
                onClick={onCheckout}
                className="w-full bg-[#2C2416] text-white py-4 rounded-2xl font-bold text-base hover:bg-[#4A7C59] transition-colors"
              >
                Оформить заказ
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ─── CheckoutModal ────────────────────────────────────────────────────────────

function CheckoutModal({
  items,
  total,
  onClose,
  onPriceChange,
}: {
  items: CartItem[]
  total: number
  onClose: (cleared: boolean) => void
  onPriceChange: (id: number, price: number) => void
}) {
  const [step, setStep] = useState<CheckoutStep>('form')
  const [form, setForm] = useState({ name: '', email: '', phone: '', comment: '' })
  const [payment, setPayment] = useState<'card' | 'sbp' | 'transfer'>('card')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [orderError, setOrderError] = useState('')

  // Если цена меньше minPrice — ставим minPrice
  useEffect(() => {
    items.forEach(item => {
      const min = item.artwork.minPrice || 500
      if (item.artwork.price < min) onPriceChange(item.artwork.id, min)
    })
  }, [])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  function validate() {
    const e: Record<string, string> = {}
    if (!form.name.trim()) e.name = 'Введите имя'
    if (!form.email.includes('@')) e.email = 'Введите корректный email'
    if (!form.phone.trim()) e.phone = 'Введите телефон'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  function handleFormSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (validate()) setStep('payment')
  }

  async function handlePaySubmit() {
    setLoading(true)
    setOrderError('')
    
    try {
      const items_payload = items.map(item => ({
        picture_id: item.artwork.id,
        offered_price: item.artwork.price,
      }))
      
      const response = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: form.name,
          customer_email: form.email,
          customer_phone: form.phone,
          items: items_payload,
        }),
      })

      const data = await response.json()

      if (response.ok && data.payment_status === 'paid') {
        setStep('success')
      } else if (response.status === 402 || data.payment_status === 'failed') {
        setOrderError('Платёж отклонен. Пожалуйста, проверьте номер телефона и попробуйте снова.')
        setStep('payment')
      } else {
        setOrderError(data.detail || 'Произошла ошибка при создании заказа')
        setStep('payment')
      }
    } catch (error) {
      setOrderError('Ошибка подключения. Пожалуйста, проверьте интернет и попробуйте снова.')
      setStep('payment')
      console.error('Order error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div
        className="bg-[#FFFCF7] rounded-3xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {step === 'success' ? (
          <div className="p-12 text-center">
            <div className="text-7xl mb-6">🎨</div>
            <h2 className="font-serif text-3xl text-[#2C2416] mb-3">Спасибо за поддержку!</h2>
            <p className="text-[#6B5B42] leading-relaxed mb-3">
              Ваш заказ принят и будет обработан в течение одного рабочего дня. Подтверждение отправлено на <strong>{form.email}</strong>.
            </p>
            <p className="text-sm text-[#A89070] mb-8">
              Покупая работы наших детей, вы помогаете им расти, верить в себя и видеть мир прекрасным. Это важнее, чем кажется.
            </p>
            <div className="bg-[#E8F2EB] rounded-2xl p-4 mb-6 text-sm text-[#4A7C59]">
              🌱 <strong>{fmt(Math.round(total * 0.3))}</strong> из вашего заказа поступят в фонд «Искусство чтобы жить»
            </div>
            <button
              onClick={() => onClose(true)}
              className="bg-[#4A7C59] text-white px-8 py-3.5 rounded-2xl font-bold hover:bg-[#3D6649] transition-colors"
            >
              Вернуться на сайт
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between p-6 border-b border-[#E8DCC8]">
              <div>
                <h2 className="font-serif text-xl text-[#2C2416]">
                  {step === 'form' ? 'Оформление заказа' : 'Оплата'}
                </h2>
                <div className="flex gap-2 mt-2">
                  {(['form', 'payment'] as const).map((s, i) => (
                    <div
                      key={s}
                      className={`h-1 rounded-full transition-all ${
                        step === s ? 'w-8 bg-[#4A7C59]' : step === 'success' || (s === 'form' && step === 'payment') ? 'w-6 bg-[#7AAD87]' : 'w-6 bg-[#E8DCC8]'
                      }`}
                    />
                  ))}
                </div>
              </div>
              <button
                onClick={() => onClose(false)}
                className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-[#F0E8D8] text-[#6B5B42] transition-colors"
              >
                ✕
              </button>
            </div>

            {step === 'form' && (
              <form onSubmit={handleFormSubmit} className="p-6 space-y-4">
                <div className="bg-[#F5EFE3] rounded-xl p-3 text-sm text-[#6B5B42] mb-2">
                  Итого: <strong>{fmt(total)}</strong> · {items.length} работ(ы)
                </div>
                {[
                  { key: 'name', label: 'Имя', placeholder: 'Иван Петров', type: 'text' },
                  { key: 'email', label: 'Email', placeholder: 'ivan@mail.ru', type: 'email' },
                  { key: 'phone', label: 'Телефон', placeholder: '+7 999 123-45-67', type: 'tel' },
                ].map(f => (
                  <div key={f.key}>
                    <label className="block text-sm font-semibold text-[#6B5B42] mb-1">{f.label}</label>
                    <input
                      type={f.type}
                      placeholder={f.placeholder}
                      value={form[f.key as keyof typeof form]}
                      onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                      className={`w-full border rounded-xl px-4 py-3 text-sm bg-white text-[#2C2416] placeholder-[#C8B89A] outline-none transition-colors focus:border-[#4A7C59] focus:ring-2 focus:ring-[#4A7C59]/20 ${
                        errors[f.key] ? 'border-[#E07A5F]' : 'border-[#E8DCC8]'
                      }`}
                    />
                    {errors[f.key] && <p className="text-xs text-[#E07A5F] mt-1">{errors[f.key]}</p>}
                  </div>
                ))}
                <div>
                  <label className="block text-sm font-semibold text-[#6B5B42] mb-1">Комментарий (необязательно)</label>
                  <textarea
                    placeholder="Пожелания или вопросы по заказу"
                    rows={3}
                    value={form.comment}
                    onChange={e => setForm(prev => ({ ...prev, comment: e.target.value }))}
                    className="w-full border border-[#E8DCC8] rounded-xl px-4 py-3 text-sm bg-white text-[#2C2416] placeholder-[#C8B89A] outline-none focus:border-[#4A7C59] focus:ring-2 focus:ring-[#4A7C59]/20 resize-none"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full bg-[#2C2416] text-white py-3.5 rounded-2xl font-bold hover:bg-[#4A7C59] transition-colors mt-2"
                >
                  Продолжить к оплате →
                </button>
              </form>
            )}

            {step === 'payment' && (
              <div className="p-6">
                <p className="text-sm text-[#6B5B42] mb-4">
                  Выберите способ оплаты для заказа на <strong>{fmt(total)}</strong>
                </p>
                {orderError && (
                  <div className="bg-[#FEE2E2] rounded-xl p-3 mb-4 text-sm text-[#991B1B]">
                    ⚠️ {orderError}
                  </div>
                )}
                <div className="space-y-3 mb-6">
                  {[
                    { key: 'card' as const, icon: '💳', label: 'Банковская карта', sub: 'Visa, Mastercard, МИР' },
                    { key: 'sbp' as const, icon: '📱', label: 'СБП', sub: 'Система быстрых платежей' },
                    { key: 'transfer' as const, icon: '🏦', label: 'Банковский перевод', sub: 'По реквизитам фонда' },
                  ].map(opt => (
                    <label
                      key={opt.key}
                      className={`flex items-center gap-4 p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                        payment === opt.key
                          ? 'border-[#4A7C59] bg-[#E8F2EB]'
                          : 'border-[#E8DCC8] bg-white hover:border-[#7AAD87]'
                      }`}
                    >
                      <input
                        type="radio"
                        className="sr-only"
                        checked={payment === opt.key}
                        onChange={() => setPayment(opt.key)}
                      />
                      <span className="text-2xl">{opt.icon}</span>
                      <div>
                        <p className="font-semibold text-sm text-[#2C2416]">{opt.label}</p>
                        <p className="text-xs text-[#A89070]">{opt.sub}</p>
                      </div>
                      <div
                        className={`ml-auto w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                          payment === opt.key ? 'border-[#4A7C59]' : 'border-[#E8DCC8]'
                        }`}
                      >
                        {payment === opt.key && <div className="w-2.5 h-2.5 rounded-full bg-[#4A7C59]" />}
                      </div>
                    </label>
                  ))}
                </div>
                <div className="bg-[#FBF0EC] rounded-xl p-3 mb-6 text-xs text-[#A05A3F]">
                  🎨 Ваша покупка поддерживает юных художников — <strong>{fmt(Math.round(total * 0.3))}</strong> направится в фонд
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => setStep('form')}
                    disabled={loading}
                    className="flex-1 border border-[#E8DCC8] text-[#6B5B42] py-3.5 rounded-2xl font-semibold hover:bg-[#F5EFE3] transition-colors disabled:opacity-50"
                  >
                    ← Назад
                  </button>
                  <button
                    onClick={handlePaySubmit}
                    disabled={loading}
                    className="flex-[2] bg-[#2C2416] text-white py-3.5 rounded-2xl font-bold hover:bg-[#4A7C59] transition-colors disabled:opacity-50"
                  >
                    {loading ? 'Обработка...' : `Оплатить ${fmt(total)}`}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ─── DonationSection ──────────────────────────────────────────────────────────

function DonationSection() {
  const amounts = [300, 500, 1000, 2000, 5000]
  const [selected, setSelected] = useState(500)
  const [custom, setCustom] = useState('')
  const [donated, setDonated] = useState(false)

  const finalAmount = custom ? parseInt(custom) || 0 : selected

  function handleDonate() {
    if (finalAmount > 0) {
      setDonated(true)
      setTimeout(() => setDonated(false), 3000)
    }
  }

  return (
    <section id="donate" className="bg-[#2C2416] py-20 px-4">
      <div className="max-w-3xl mx-auto text-center">
        <span className="text-[#D4A853] text-sm font-bold uppercase tracking-widest">Сделать доброе дело</span>
        <h2 className="font-serif text-4xl md:text-5xl text-white mt-3 mb-4">
          Поддержите фонд напрямую
        </h2>
        <p className="text-[#C8B89A] text-lg leading-relaxed mb-10 max-w-2xl mx-auto">
          Ваше пожертвование помогает детям получить художественные материалы, участвовать в выставках и верить в своё творчество. Даже небольшая сумма имеет значение.
        </p>

        <div className="flex flex-wrap justify-center gap-3 mb-6">
          {amounts.map(a => (
            <button
              key={a}
              onClick={() => { setSelected(a); setCustom('') }}
              className={`px-6 py-3 rounded-2xl font-bold transition-all ${
                selected === a && !custom
                  ? 'bg-[#D4A853] text-[#2C2416]'
                  : 'bg-white/10 text-white hover:bg-white/20 border border-white/20'
              }`}
            >
              {fmt(a)}
            </button>
          ))}
        </div>

        <div className="flex gap-3 mb-8 max-w-sm mx-auto">
          <input
            type="number"
            placeholder="Своя сумма, ₽"
            value={custom}
            onChange={e => { setCustom(e.target.value); setSelected(0) }}
            className="flex-1 bg-white/10 border border-white/20 rounded-2xl px-4 py-3 text-white placeholder-white/40 outline-none focus:border-[#D4A853] focus:ring-2 focus:ring-[#D4A853]/20 text-center font-semibold"
          />
        </div>

        <button
          onClick={handleDonate}
          className={`px-12 py-4 rounded-2xl font-bold text-lg transition-all duration-300 ${
            donated
              ? 'bg-[#4A7C59] text-white'
              : 'bg-[#D4A853] text-[#2C2416] hover:bg-[#E5B860] hover:scale-105'
          }`}
        >
          {donated ? '💛 Спасибо за вашу поддержку!' : `Пожертвовать ${finalAmount > 0 ? fmt(finalAmount) : ''}`}
        </button>

        <div className="grid grid-cols-3 gap-6 mt-14 pt-10 border-t border-white/10">
          {[
            { num: '847', label: 'детей поддержаны' },
            { num: '2 340', label: 'работ продано' },
            { num: '4.2 млн', label: 'рублей собрано' },
          ].map(s => (
            <div key={s.label}>
              <div className="font-serif text-3xl text-[#D4A853]">{s.num}</div>
              <div className="text-[#C8B89A] text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── ContactSection ───────────────────────────────────────────────────────────

function ContactSection() {
  const [form, setForm] = useState({ name: '', email: '', message: '' })
  const [sent, setSent] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSent(true)
    setForm({ name: '', email: '', message: '' })
    setTimeout(() => setSent(false), 4000)
  }

  return (
    <section id="contact" className="py-20 px-4 bg-[#F5EFE3]">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-[#4A7C59] text-sm font-bold uppercase tracking-widest">Свяжитесь с нами</span>
          <h2 className="font-serif text-4xl text-[#2C2416] mt-3">Мы рады вашим вопросам</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <p className="text-[#6B5B42] leading-relaxed mb-8">
              Если вы хотите стать партнёром фонда, предложить сотрудничество, помочь с организацией выставки или просто поговорить — пишите нам. Мы отвечаем в течение одного рабочего дня.
            </p>
            <div className="space-y-4">
              {[
                { icon: '📬', label: 'Email', value: 'hello@kraskiland.ru' },
                { icon: '📞', label: 'Телефон', value: '+7 (495) 123-45-67' },
                { icon: '📍', label: 'Адрес', value: 'Москва, ул. Творческая, 12, офис 3' },
                { icon: '🕐', label: 'Режим работы', value: 'Пн–Пт, 10:00–18:00' },
              ].map(c => (
                <div key={c.label} className="flex gap-3 items-start">
                  <span className="text-xl mt-0.5">{c.icon}</span>
                  <div>
                    <p className="text-xs text-[#A89070] font-semibold">{c.label}</p>
                    <p className="text-[#2C2416] font-medium">{c.value}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: 'name', label: 'Ваше имя', placeholder: 'Как к вам обращаться?', type: 'text' },
              { key: 'email', label: 'Email', placeholder: 'Для ответа', type: 'email' },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-sm font-semibold text-[#6B5B42] mb-1">{f.label}</label>
                <input
                  type={f.type}
                  placeholder={f.placeholder}
                  value={form[f.key as keyof typeof form]}
                  onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                  className="w-full border border-[#E8DCC8] rounded-xl px-4 py-3 text-sm bg-white text-[#2C2416] placeholder-[#C8B89A] outline-none focus:border-[#4A7C59] focus:ring-2 focus:ring-[#4A7C59]/20"
                />
              </div>
            ))}
            <div>
              <label className="block text-sm font-semibold text-[#6B5B42] mb-1">Сообщение</label>
              <textarea
                placeholder="Расскажите, чем мы можем помочь или чем хотите помочь вы"
                rows={5}
                value={form.message}
                onChange={e => setForm(p => ({ ...p, message: e.target.value }))}
                className="w-full border border-[#E8DCC8] rounded-xl px-4 py-3 text-sm bg-white text-[#2C2416] placeholder-[#C8B89A] outline-none focus:border-[#4A7C59] focus:ring-2 focus:ring-[#4A7C59]/20 resize-none"
              />
            </div>
            {sent && (
              <div className="bg-[#E8F2EB] text-[#4A7C59] text-sm px-4 py-3 rounded-xl font-semibold">
                ✓ Сообщение отправлено! Мы ответим вам скоро.
              </div>
            )}
            <button
              type="submit"
              className="w-full bg-[#4A7C59] text-white py-3.5 rounded-2xl font-bold hover:bg-[#3D6649] transition-colors"
            >
              Отправить сообщение
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [artworks, setArtworks] = useState<Artwork[]>(ARTWORKS)
  const [cart, setCart] = useState<CartItem[]>([])

  function handlePriceChange(id: number, price: number) {
    setCart(prev => prev.map(item =>
      item.artwork.id === id
        ? { ...item, artwork: { ...item.artwork, price } }
        : item
    ))
  }
  const [cartOpen, setCartOpen] = useState(false)
  const [checkoutOpen, setCheckoutOpen] = useState(false)
  const [selectedArtwork, setSelectedArtwork] = useState<Artwork | null>(null)
  const [filter, setFilter] = useState<FilterCategory>('all')
  const [sort, setSort] = useState<SortKey>('popular')
  const [footerInfo, setFooterInfo] = useState<string | null>(null)
  const [scrolled, setScrolled] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    fetch('/api/pictures', { signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error(`Pictures API returned ${response.status}`)
        return response.json() as Promise<Artwork[]>
      })
      .then(pictures => setArtworks(pictures))
      .catch(error => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        console.error('Failed to load pictures:', error)
      })

    return () => controller.abort()
  }, [])

  const cartCount = cart.reduce((s, i) => s + i.qty, 0)
  const cartTotal = cart.reduce((s, i) => s + i.artwork.price * i.qty, 0)

  function addToCart(artwork: Artwork) {
    setCart(prev => {
      const existing = prev.find(i => i.artwork.id === artwork.id)
      if (existing) return prev
      return [...prev, { artwork: { ...artwork, price: artwork.minPrice || 500 }, qty: 1 }]
    })
  }

  function handleBuy(artwork: Artwork, price: number) {
    const finalPrice = price || artwork.minPrice || 500
    setCart(prev => {
      const existing = prev.find(i => i.artwork.id === artwork.id)
      if (existing) {
        return prev.map(i => 
          i.artwork.id === artwork.id 
            ? { ...i, artwork: { ...i.artwork, price: finalPrice }, qty: 1 }
            : i
        )
      }
      return [...prev, { artwork: { ...artwork, price: finalPrice }, qty: 1 }]
    })
    setCartOpen(false)
    setCheckoutOpen(true)
  }

  function removeFromCart(id: number) {
    setCart(prev => prev.filter(i => i.artwork.id !== id))
  }

  function changeQty(id: number, qty: number) {
    if (qty <= 0) return removeFromCart(id)
    setCart(prev => prev.map(i => i.artwork.id === id ? { ...i, qty } : i))
  }

  const filteredSorted = [...artworks]
    .filter(a => {
      if (filter === 'all') return true
      if (filter === 'new') return a.isNew
      return a.category === filter
    })
    .sort((a, b) => {
      if (sort === 'popular') return b.popularity - a.popularity
      if (sort === 'price-asc') return a.price - b.price
      if (sort === 'price-desc') return b.price - a.price
      if (sort === 'newest') return (b.isNew ? 1 : 0) - (a.isNew ? 1 : 0)
      return 0
    })

  const featured = artworks.filter(a => a.isFeatured).slice(0, 3)

  return (
    <div className="min-h-screen bg-[#FEFAF4]">

      {/* ── Navigation ── */}
      <nav
        className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 ${
          scrolled ? 'bg-[#FFFCF7]/95 backdrop-blur-md shadow-sm border-b border-[#E8DCC8]' : 'bg-transparent'
        }`}
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <button
  onClick={() => scrollTo('hero')}
  className="flex items-center gap-2.5"
>
  <img
    src="/logo.png"
    alt="Логотип «Искусство чтобы жить»"
    className="w-10 h-10 rounded-full object-cover"
  />
  <span
  className={`font-serif text-lg font-bold whitespace-nowrap transition-colors duration-300 ${
    scrolled ? 'text-[#4A7C59]' : 'text-[#FEFAF4]'
  }`}
>
  Искусство чтобы жить
</span>
</button>

          <div className="hidden md:flex items-center gap-6">
            {[
              { label: 'О фонде', id: 'about' },
              { label: 'Галерея', id: 'gallery' },
              { label: 'Поддержать', id: 'donate' },
              { label: 'Контакты', id: 'contact' },
            ].map(nav => (
              <button
                key={nav.id}
                onClick={() => scrollTo(nav.id)}
                className="text-sm font-semibold text-[#6B5B42] hover:text-[#4A7C59] transition-colors"
              >
                {nav.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setCartOpen(true)}
              className="relative flex items-center gap-2 bg-[#2C2416] text-white px-4 py-2 rounded-2xl text-sm font-semibold hover:bg-[#4A7C59] transition-colors"
            >
              <span>🛒</span>
              <span className="hidden sm:inline">Корзина</span>
              {cartCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 bg-[#E07A5F] text-white text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center leading-none">
                  {cartCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setMobileMenuOpen(o => !o)}
              className="md:hidden w-9 h-9 flex items-center justify-center rounded-xl hover:bg-[#F0E8D8] text-[#6B5B42] transition-colors"
            >
              {mobileMenuOpen ? '✕' : '☰'}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden bg-[#FFFCF7] border-t border-[#E8DCC8] px-4 py-4 space-y-1">
            {[
              { label: 'О фонде', id: 'about' },
              { label: 'Галерея', id: 'gallery' },
              { label: 'Поддержать фонд', id: 'donate' },
              { label: 'Контакты', id: 'contact' },
            ].map(nav => (
              <button
                key={nav.id}
                onClick={() => { scrollTo(nav.id); setMobileMenuOpen(false) }}
                className="block w-full text-left px-4 py-3 rounded-xl text-[#6B5B42] font-semibold hover:bg-[#F0E8D8] hover:text-[#4A7C59] transition-colors"
              >
                {nav.label}
              </button>
            ))}
          </div>
        )}
      </nav>

      {/* ── Hero ── */}
      <section id="hero" className="relative min-h-screen flex items-center overflow-hidden">
        <div className="absolute inset-0 bg-[#2C2416]">
          <img
            src="https://images.unsplash.com/photo-1536221993589-9edbbca2c7fc?w=1600&h=900&fit=crop&auto=format"
            alt="Ребёнок рисует акварелью"
            className="w-full h-full object-cover opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#2C2416]/80 via-[#2C2416]/50 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#2C2416]/60 via-transparent to-transparent" />
        </div>

        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-32 pt-40">
          <div className="max-w-2xl">
            <span className="inline-block bg-[#D4A853]/20 border border-[#D4A853]/40 text-[#D4A853] text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded-full mb-6">
              Благотворительный фонд
            </span>
            <h1 className="font-serif text-5xl sm:text-6xl md:text-7xl text-white leading-tight mb-6">
              Каждый рисунок —<br />
              <em className="not-italic text-[#7AAD87]">маленькое чудо</em>
            </h1>
            <p className="text-[#D4C8B4] text-xl leading-relaxed mb-10 max-w-xl">
              Мы помогаем детям из уязвимых семей раскрыть свой творческий потенциал. Покупайте их работы — и становитесь частью их истории.
            </p>
            <div className="flex flex-wrap gap-4">
              <button
                onClick={() => scrollTo('gallery')}
                className="bg-white text-[#2C2416] px-7 py-4 rounded-2xl font-bold text-base hover:bg-[#F5EFE3] transition-all hover:scale-105"
              >
                Посмотреть работы
              </button>
              <button
                onClick={() => scrollTo('donate')}
                className="bg-[#4A7C59] text-white px-7 py-4 rounded-2xl font-bold text-base hover:bg-[#3D6649] transition-all hover:scale-105"
              >
                Поддержать фонд
              </button>
              <button
                onClick={() => scrollTo('about')}
                className="border border-white/40 text-white px-7 py-4 rounded-2xl font-semibold text-base hover:bg-white/10 transition-all"
              >
                О фонде
              </button>
            </div>
          </div>
        </div>

        {/* Scroll hint */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-white/50">
          <span className="text-xs font-medium tracking-widest uppercase">Листайте</span>
          <div className="w-px h-8 bg-white/30 animate-pulse" />
        </div>
      </section>

      {/* ── Stats bar ── */}
      <div className="bg-white border-b border-[#E8DCC8]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 grid grid-cols-2 sm:grid-cols-4 gap-6 divide-x divide-[#E8DCC8]">
          {[
            { num: '847', label: 'детей в программе' },
            { num: '2 340', label: 'работ в галерее' },
            { num: '12', label: 'лет работаем' },
            { num: '4.2 млн ₽', label: 'собрано за год' },
          ].map((s, i) => (
            <div key={s.label} className={`text-center ${i > 0 ? 'pl-6' : ''}`}>
              <div className="font-serif text-2xl sm:text-3xl text-[#4A7C59]">{s.num}</div>
              <div className="text-xs sm:text-sm text-[#A89070] mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── About ── */}
      <section id="about" className="py-20 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-16 items-center">
          <div className="relative">
            <div className="relative rounded-3xl overflow-hidden bg-[#F0E8D8]" style={{ aspectRatio: '4/3' }}>
              <img
                src="https://images.unsplash.com/photo-1614712201488-9942af86b87b?w=800&h=600&fit=crop&auto=format"
                alt="Девочка рисует, склонившись над листом бумаги"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="absolute -bottom-6 -right-6 bg-[#D4A853] text-[#2C2416] rounded-2xl p-5 shadow-lg">
              <div className="font-serif text-3xl">2012</div>
              <div className="text-xs font-bold mt-0.5">основан фонд</div>
            </div>
            <div className="absolute -top-4 -left-4 bg-[#E8F2EB] border border-[#7AAD87] rounded-2xl p-4">
              <div className="text-2xl mb-1">🎨</div>
              <div className="text-xs font-bold text-[#4A7C59]">+180 новых<br/>работ в году</div>
            </div>
          </div>
          <div>
            <span className="text-[#4A7C59] text-sm font-bold uppercase tracking-widest">О фонде</span>
            <h2 className="font-serif text-4xl md:text-5xl text-[#2C2416] mt-3 mb-6 leading-tight">
              Мы верим, что каждый ребёнок — художник
            </h2>
            <p className="text-[#6B5B42] leading-relaxed mb-5 text-lg">
              Фонд «Искусство чтобы жить» основан в 2012 году группой педагогов и художников. Мы работаем с детьми из малообеспеченных семей, сиротами и детьми с особенностями развития — и помогаем им найти себя через искусство.
            </p>
            <p className="text-[#6B5B42] leading-relaxed mb-8">
              Наши студии работают в восьми городах России. Каждый ребёнок получает бесплатные материалы, занятия и возможность показать свои работы на выставке или продать их через нашу галерею. Вырученные средства идут обратно в фонд — и помогают следующему ребёнку.
            </p>
            <div className="grid grid-cols-3 gap-4">
              {[
                { icon: '🏫', label: '8 городов', sub: 'работы студий' },
                { icon: '📚', label: 'Бесплатно', sub: 'для всех детей' },
                { icon: '🌱', label: '30% с продаж', sub: 'возвращается в фонд' },
              ].map(v => (
                <div key={v.label} className="bg-[#F5EFE3] rounded-2xl p-4 text-center">
                  <div className="text-2xl mb-1">{v.icon}</div>
                  <div className="font-bold text-sm text-[#2C2416]">{v.label}</div>
                  <div className="text-xs text-[#A89070] mt-0.5">{v.sub}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Featured works ── */}
      <section className="py-16 px-4 sm:px-6 bg-[#F5EFE3]">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-end justify-between mb-10">
            <div>
              <span className="text-[#4A7C59] text-sm font-bold uppercase tracking-widest">Выбор редакции</span>
              <h2 className="font-serif text-3xl sm:text-4xl text-[#2C2416] mt-2">Особенные работы</h2>
            </div>
            <button
              onClick={() => scrollTo('gallery')}
              className="hidden sm:block text-sm font-semibold text-[#4A7C59] hover:text-[#2C2416] transition-colors"
            >
              Все работы →
            </button>
          </div>
          <div className="grid sm:grid-cols-3 gap-6">
            {featured.map(artwork => (
              <ArtworkCard
                key={artwork.id}
                artwork={artwork}
                onView={() => setSelectedArtwork(artwork)}
                onAdd={() => addToCart(artwork)}
                onBuy={handleBuy}
                inCart={cart.some(i => i.artwork.id === artwork.id)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── Full Gallery ── */}
      <section id="gallery" className="py-20 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-10">
            <span className="text-[#4A7C59] text-sm font-bold uppercase tracking-widest">Онлайн-галерея</span>
            <h2 className="font-serif text-4xl md:text-5xl text-[#2C2416] mt-3 mb-4">Работы наших художников</h2>
            <p className="text-[#6B5B42] max-w-lg mx-auto">
              Каждая работа — это история ребёнка. Покупая её, вы становитесь частью этой истории.
            </p>
          </div>

          {/* Filters & Sort */}

          {/* Grid */}
          <div className="gallery-grid">
            {filteredSorted.map(artwork => (
              <ArtworkCard
                key={artwork.id}
                artwork={artwork}
                onView={() => setSelectedArtwork(artwork)}
                onAdd={() => addToCart(artwork)}
                onBuy={handleBuy}
                inCart={cart.some(i => i.artwork.id === artwork.id)}
              />
            ))}
          </div>

          {filteredSorted.length === 0 && (
            <div className="text-center py-20 text-[#A89070]">
              <div className="text-4xl mb-3">🎨</div>
              <p className="font-serif text-xl">Работ не найдено</p>
              <p className="text-sm mt-1">Попробуйте другой фильтр</p>
            </div>
          )}
        </div>
      </section>

      {/* ── Donation ── */}
      <DonationSection />

      {/* ── Contact ── */}
      <ContactSection />

      {/* ── Footer ── */}
      <footer className="bg-[#2C2416] py-12 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-8 mb-10">
            <div>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="w-8 h-8 bg-[#4A7C59] rounded-xl flex items-center justify-center text-white text-lg font-bold" style={{ fontFamily: 'var(--font-serif)' }}>К</div>
                <span className="font-serif text-white text-lg">Искусство чтобы жить</span>
              </div>
              <p className="text-[#A89070] text-sm leading-relaxed">
                Благотворительный фонд поддержки детского творчества. Работаем с 2012 года.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4 text-sm">Фонд</h4>
              <ul className="space-y-2">
                {['О нас', 'Наши проекты', 'Отчёты', 'Партнёры'].map(l => (
                  <li key={l}><button onClick={() => setFooterInfo(l)} className="text-[#A89070] text-sm hover:text-white cursor-pointer transition-colors text-left">{l}</button></li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4 text-sm">Галерея</h4>
              <ul className="space-y-2">
                {['Все работы', 'Живопись', 'Рисунки', 'Цифровое искусство'].map(l => (
                  <li key={l}><button onClick={() => setFooterInfo(l)} className="text-[#A89070] text-sm hover:text-white cursor-pointer transition-colors text-left">{l}</button></li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4 text-sm">Помочь</h4>
              <ul className="space-y-2">
                {['Пожертвовать', 'Купить работу', 'Стать волонтёром', 'Корпоративное партнёрство'].map(l => (
                  <li key={l}><button onClick={() => setFooterInfo(l)} className="text-[#A89070] text-sm hover:text-white cursor-pointer transition-colors text-left">{l}</button></li>
                ))}
              </ul>
            </div>
          </div>
          <div className="border-t border-white/10 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-[#6B5B42] text-xs">© 2024 Благотворительный фонд «Искусство чтобы жить». Все права защищены.</p>
            <p className="text-[#6B5B42] text-xs">ИНН 7712345678 · ОГРН 1127799000001</p>
          </div>
        </div>
      </footer>

      {/* ── Footer info modal ── */}
      {footerInfo && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setFooterInfo(null)}>
          <div className="bg-[#FBF7EE] rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-8" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-serif text-2xl text-[#2C2416]">{footerInfo}</h3>
              <button onClick={() => setFooterInfo(null)} className="text-[#6B5B42] hover:text-[#2C2416] text-2xl leading-none" aria-label="Закрыть">×</button>
            </div>
            {(FOOTER_INFO[footerInfo] || ['Раздел наполняется командой фонда.']).map((par, i) => (
              <p key={i} className="text-[#6B5B42] leading-relaxed mb-4">{par}</p>
            ))}
          </div>
        </div>
      )}

      {/* ── Modals & Sidebars ── */}
      {selectedArtwork && (
        <ArtworkModal
          artwork={selectedArtwork}
          onClose={() => setSelectedArtwork(null)}
          onBuy={handleBuy}
        />
      )}

      {cartOpen && (
        <CartSidebar
          items={cart}
          onClose={() => setCartOpen(false)}
          onRemove={removeFromCart}
          onChangeQty={changeQty}
          onCheckout={() => { setCartOpen(false); setCheckoutOpen(true) }}
          onPriceChange={handlePriceChange}
        />
      )}

      {checkoutOpen && (
        <CheckoutModal
          items={cart}
          total={cartTotal}
          onClose={(cleared) => {
            setCheckoutOpen(false)
            if (cleared) setCart([])
          }}
          onPriceChange={handlePriceChange}
        />
      )}
    </div>
  )
}
