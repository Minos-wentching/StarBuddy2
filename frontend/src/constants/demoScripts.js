export const demoScripts = [
  {
    id: 'pressure-collapse',
    title: '高压崩溃线',
    theme: '在高压工作中，保护者与受伤部分争夺控制权。',
    durationSec: 78,
    presetAnswers: {
      question_1: '我印象最深的是临近汇报前连续失眠，白天强撑，晚上会突然崩溃。最不想被看到的是无助和疲惫。',
      question_2: '压力大时我会听到“不能停，一停就会被淘汰”。我会形容自己是高敏感、责任感强、容易自我施压的人。',
    },
    personaSeed: {
      persona: 'firefighters',
      intensity: 0.82,
      council_topic: '如何在高压任务下，既保住表现，又不再以自我攻击推进？',
    },
    memoryOrbSeed: [
      {
        id: 'pressure_orb_1',
        title: '绩效压顶',
        trauma_text: '连续冲刺阶段，害怕一停就失去价值。',
        trigger_event: '汇报前两晚失眠',
        intensity: 0.86,
        persona_hint: 'firefighters',
      },
      {
        id: 'pressure_orb_2',
        title: '害怕掉队',
        trauma_text: '对“落后就会被否定”的担心长期存在。',
        trigger_event: '看到他人进展后出现胸闷',
        intensity: 0.72,
        persona_hint: 'exiles',
      },
      {
        id: 'pressure_orb_3',
        title: '盔甲模式',
        trauma_text: '习惯把任务排满，避免直面脆弱。',
        trigger_event: '情绪上来时继续加班',
        intensity: 0.68,
        persona_hint: 'firefighters',
      },
    ],
    scenes: [
      { atMs: 0, type: 'user_message', payload: { content: '我快撑不住了，最近每天都像在打仗。' } },
      { atMs: 1800, type: 'assistant_message', payload: { persona: 'manager', emotionIntensity: 0.46, content: '我听见你的疲惫了。先别急着解决问题，我们先一起把这股“快要垮掉”的感觉放到台面上。' } },
      { atMs: 4200, type: 'counselor_report', payload: {
        core_beliefs: [
          { belief_id: 'p1', content: '只要停下来，我就会被淘汰', valence: -0.7, intensity: 8.7, origin_event: '长期绩效压力' },
          { belief_id: 'p2', content: '我必须永远表现得足够强', valence: -0.6, intensity: 8.1, origin_event: '过往失败经历' }
        ],
        trigger_event: '临近汇报节点，连续两晚失眠',
        emotional_summary: '系统处于高警觉状态，保护机制全面接管。',
        self_presence: {
          clarity: 0.42,
          compassion: 0.39,
          trend: 'down',
          analysis: '高压触发导致觉察与接纳下降，系统进入应激收缩。'
        }
      } },
      { atMs: 6800, type: 'persona_switch', payload: { persona: 'firefighters', intensity: 0.83, reason: 'threshold_switch' } },
      { atMs: 8600, type: 'assistant_message', payload: { persona: 'firefighters', emotionIntensity: 0.83, content: '别停。继续冲。只要你还在跑，就不会被看穿脆弱。' } },
      { atMs: 11800, type: 'council_start', payload: { council_id: 'demo_council_pressure', total_rounds: 2 } },
      { atMs: 15000, type: 'council_round', payload: {
        round: 1,
        council_id: 'demo_council_pressure',
        total_rounds: 2,
        exiles_argument: '我只是很害怕被否定，我真的很累。',
        firefighters_argument: '脆弱会让我们失去位置，必须硬撑。',
        counselor_analysis: '双方都在保护“价值感”，只是策略不同。'
      } },
      { atMs: 21000, type: 'council_round', payload: {
        round: 2,
        council_id: 'demo_council_pressure',
        total_rounds: 2,
        exiles_argument: '如果有人能允许我休息一下，我也许就不会这么绝望。',
        firefighters_argument: '可以休息，但需要有边界和节奏。',
        counselor_analysis: '开始出现协商：效率与照顾并非二选一。'
      } },
      { atMs: 26200, type: 'council_end', payload: { conclusion: '共识：采用“90分钟专注 + 15分钟恢复”的节律，允许情绪波动存在。' } },
      { atMs: 30200, type: 'persona_switch', payload: { persona: 'manager', intensity: 0.55, reason: 'return_threshold' } },
      { atMs: 33300, type: 'assistant_message', payload: { persona: 'manager', emotionIntensity: 0.55, content: '你不需要一直靠硬扛证明自己。我们已经找到一种更可持续的方式。' } },
      { atMs: 36000, type: 'diary_update', payload: { persona: 'firefighters', text: '我以为不停跑就能安全，原来我也只是怕被抛下。', image_url: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=1200&q=80&auto=format&fit=crop' } },
      { atMs: 38600, type: 'report_hint', payload: {
        core_beliefs: [
          { belief_id: 'p1', content: '只要停下来，我就会被淘汰', valence: -0.7, intensity: 8.7 },
          { belief_id: 'p2', content: '我必须永远表现得足够强', valence: -0.6, intensity: 8.1 }
        ],
        persona_portraits: {
          exiles: '一个抱着膝盖坐在楼梯间的小孩，害怕自己不够好。',
          firefighters: '穿着盔甲不停前进的骑士，拒绝停下。'
        },
        council_summary: '系统从“硬扛”转向“有节律地推进”。',
        emotion_trend: [0.83, 0.79, 0.72, 0.66, 0.61, 0.55],
        self_presence: 0.58,
        self_presence_trend: '持续提升中',
        counselor_note: '你正在学习把效率与自我照顾放到同一张桌子上。'
      } },
      { atMs: 42000, type: 'narrative_chapter', payload: {
        title: '在盔甲与疲惫之间',
        content: '她曾把奔跑当作唯一安全感。直到那场星球会议，让她第一次承认：真正想守护的不是成绩，而是还愿意感受的自己。',
        image_url: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1200&q=80&auto=format&fit=crop'
      } },
      { atMs: 45500, type: 'social_hint', payload: {
        similarUsers: [
          {
            anonymous_id: 9911,
            similarity: 0.91,
            shared_beliefs: ['我不能停', '努力才有价值'],
            exiles_summary: '害怕被否定，总在深夜自责。',
            firefighters_summary: '把任务排满，以忙碌压住焦虑。',
            can_chat: true,
            profile_kind: 'guide'
          }
        ]
      } }
    ]
  },
  {
    id: 'relationship-repair',
    title: '关系修复线',
    theme: '在亲密关系中，从防御到表达真实需求。',
    durationSec: 74,
    presetAnswers: {
      question_1: '冲突时我会先沉默，但心里其实很痛。我最不想被看到的是害怕被抛下。',
      question_2: '压力大时会有声音说“先退后才安全”。我会形容自己是敏感、重感情、害怕冲突升级的人。',
    },
    personaSeed: {
      persona: 'exiles',
      intensity: 0.74,
      council_topic: '如何在关系冲突中同时守住安全感与连接感？',
    },
    memoryOrbSeed: [
      {
        id: 'relationship_orb_1',
        title: '冲突冻结',
        trauma_text: '吵架时先冷掉，其实是怕被嫌弃。',
        trigger_event: '对方语气突然提高',
        intensity: 0.75,
        persona_hint: 'exiles',
      },
      {
        id: 'relationship_orb_2',
        title: '沉默防线',
        trauma_text: '遇到争执先撤退，避免再次受伤。',
        trigger_event: '争执升级前出现回避冲动',
        intensity: 0.66,
        persona_hint: 'firefighters',
      },
      {
        id: 'relationship_orb_3',
        title: '连接渴望',
        trauma_text: '真正想表达的是“我害怕失去你”。',
        trigger_event: '关系紧张时胃部收紧',
        intensity: 0.62,
        persona_hint: 'manager',
      },
    ],
    scenes: [
      { atMs: 0, type: 'user_message', payload: { content: '我每次吵架都会先冷掉，明明心里很痛。' } },
      { atMs: 2000, type: 'assistant_message', payload: { persona: 'manager', emotionIntensity: 0.49, content: '你不是不在乎，而是系统在第一时间选择了“保护”。我们看看它在防什么。' } },
      { atMs: 4700, type: 'counselor_report', payload: {
        core_beliefs: [
          { belief_id: 'r1', content: '表达需要会被嫌弃', valence: -0.62, intensity: 7.9, origin_event: '过往关系中的忽视体验' },
          { belief_id: 'r2', content: '先撤退才能避免再次受伤', valence: -0.57, intensity: 7.2, origin_event: '冲突后的自我隔离' }
        ],
        trigger_event: '对方语气突然提高，身体出现“冻结”反应',
        emotional_summary: '系统切换到回避策略，以降低再次受伤概率。',
        self_presence: {
          clarity: 0.51,
          compassion: 0.46,
          trend: 'down',
          analysis: '冲突场景触发旧伤，表达能力下降。'
        }
      } },
      { atMs: 7600, type: 'persona_switch', payload: { persona: 'exiles', intensity: 0.74, reason: 'threshold_switch' } },
      { atMs: 9500, type: 'assistant_message', payload: { persona: 'exiles', emotionIntensity: 0.74, content: '我不是想冷漠，我只是怕一开口就被推开。' } },
      { atMs: 13000, type: 'council_start', payload: { council_id: 'demo_council_relationship', total_rounds: 2 } },
      { atMs: 16800, type: 'council_round', payload: {
        round: 1,
        council_id: 'demo_council_relationship',
        total_rounds: 2,
        exiles_argument: '我需要被理解，但我不敢说。',
        firefighters_argument: '先撤退是安全策略，不然会再次受伤。',
        counselor_analysis: '核心冲突是“连接需求”与“安全需求”的拉扯。'
      } },
      { atMs: 22400, type: 'council_round', payload: {
        round: 2,
        council_id: 'demo_council_relationship',
        total_rounds: 2,
        exiles_argument: '如果能先说“我现在很怕”，也许不会演变成冷战。',
        firefighters_argument: '允许表达，但要在情绪过载前设定暂停词。',
        counselor_analysis: '出现可执行的沟通协议。'
      } },
      { atMs: 27000, type: 'council_end', payload: { conclusion: '共识：冲突时先说情绪，再说需求；出现过载时启用“十分钟暂停词”。' } },
      { atMs: 30600, type: 'persona_switch', payload: { persona: 'manager', intensity: 0.48, reason: 'return_threshold' } },
      { atMs: 33200, type: 'assistant_message', payload: { persona: 'manager', emotionIntensity: 0.48, content: '你不是不会爱，而是一直在用旧方式自保。现在你有了新的沟通协议。' } },
      { atMs: 36000, type: 'report_hint', payload: {
        core_beliefs: [
          { belief_id: 'r1', content: '表达需要会被嫌弃', valence: -0.62, intensity: 7.9 },
          { belief_id: 'r2', content: '先撤退才能避免再次受伤', valence: -0.57, intensity: 7.2 }
        ],
        persona_portraits: {
          exiles: '站在雨中不敢敲门的人，渴望被接纳。',
          firefighters: '手握盾牌的守卫，宁可退后也不冒险。'
        },
        council_summary: '从冷战策略转向“情绪命名 + 需求表达”。',
        emotion_trend: [0.74, 0.71, 0.66, 0.59, 0.52, 0.48],
        self_presence: 0.63,
        self_presence_trend: '持续提升中',
        counselor_note: '当你允许脆弱先被看见，关系就有机会真正靠近。'
      } },
      { atMs: 39500, type: 'narrative_chapter', payload: {
        title: '先说害怕，再说需求',
        content: '她曾把沉默当盔甲。后来她学会在争执里先说“我现在很怕失去连接”。那一刻，争吵终于变成了对话。',
        image_url: 'https://images.unsplash.com/photo-1492446845049-9c50cc313f00?w=1200&q=80&auto=format&fit=crop'
      } },
      { atMs: 43000, type: 'social_hint', payload: {
        similarUsers: [
          {
            anonymous_id: 9922,
            similarity: 0.87,
            shared_beliefs: ['表达会被拒绝', '先保护自己'],
            exiles_summary: '渴望靠近却怕被误解。',
            firefighters_summary: '习惯先沉默，把冲突推迟。',
            can_chat: true,
            profile_kind: 'guide'
          }
        ]
      } }
    ]
  },
  {
    id: 'self-reconciliation',
    title: '自我和解线',
    theme: '从自我苛责走向自我接纳。',
    durationSec: 82,
    presetAnswers: {
      question_1: '每次犯错我都会反复责备自己，最不想被看到的是“我可能不够好”的恐惧。',
      question_2: '压力大时脑中会说“你必须完美”。我会形容自己是上进、认真、但容易苛责自己的人。',
    },
    personaSeed: {
      persona: 'firefighters',
      intensity: 0.79,
      council_topic: '如何保留成长动力，同时停止羞辱式自我驱动？',
    },
    memoryOrbSeed: [
      {
        id: 'self_orb_1',
        title: '完美执念',
        trauma_text: '把“值得被爱”与“必须完美”绑定在一起。',
        trigger_event: '一次普通失误后持续反刍',
        intensity: 0.81,
        persona_hint: 'firefighters',
      },
      {
        id: 'self_orb_2',
        title: '失败羞耻',
        trauma_text: '出错后会用否定语气攻击自己。',
        trigger_event: '复盘时不断放大瑕疵',
        intensity: 0.73,
        persona_hint: 'exiles',
      },
      {
        id: 'self_orb_3',
        title: '温柔重建',
        trauma_text: '希望在成长中允许不完美存在。',
        trigger_event: '尝试把批评改成支持语句',
        intensity: 0.58,
        persona_hint: 'manager',
      },
    ],
    scenes: [
      { atMs: 0, type: 'user_message', payload: { content: '我总觉得自己不够好，做什么都差一点。' } },
      { atMs: 1700, type: 'assistant_message', payload: { persona: 'manager', emotionIntensity: 0.44, content: '这句“还不够好”像一个长期驻扎的声音。我们先听清它，再决定是否继续相信它。' } },
      { atMs: 4100, type: 'counselor_report', payload: {
        core_beliefs: [
          { belief_id: 's1', content: '我必须完美才值得被爱', valence: -0.75, intensity: 8.9, origin_event: '成长中的高标准评价' },
          { belief_id: 's2', content: '出错意味着我很糟糕', valence: -0.67, intensity: 8.2, origin_event: '关键失败经历' }
        ],
        trigger_event: '一次普通失误后持续反刍',
        emotional_summary: '内在批评者持续高压输出，系统缺乏恢复空间。',
        self_presence: {
          clarity: 0.47,
          compassion: 0.34,
          trend: 'down',
          analysis: '自我接纳显著不足，认同感被成绩绑定。'
        }
      } },
      { atMs: 6800, type: 'persona_switch', payload: { persona: 'firefighters', intensity: 0.8, reason: 'threshold_switch' } },
      { atMs: 8600, type: 'assistant_message', payload: { persona: 'firefighters', emotionIntensity: 0.8, content: '再努力一点，再严一点，就不会再被说不行。' } },
      { atMs: 12000, type: 'council_start', payload: { council_id: 'demo_council_self', total_rounds: 3 } },
      { atMs: 15700, type: 'council_round', payload: {
        round: 1,
        council_id: 'demo_council_self',
        total_rounds: 3,
        exiles_argument: '我很怕被否定，我想被温柔对待。',
        firefighters_argument: '放松会带来失败，所以必须持续高压。',
        counselor_analysis: '“高压”在保护价值感，但成本过高。'
      } },
      { atMs: 21400, type: 'council_round', payload: {
        round: 2,
        council_id: 'demo_council_self',
        total_rounds: 3,
        exiles_argument: '当我犯错时，我需要的是修复，不是羞辱。',
        firefighters_argument: '可以降低攻击，但必须保留行动力。',
        counselor_analysis: '开始形成“高标准 + 低羞耻”的新框架。'
      } },
      { atMs: 26800, type: 'council_round', payload: {
        round: 3,
        council_id: 'demo_council_self',
        total_rounds: 3,
        exiles_argument: '我愿意继续努力，但也想被允许不完美。',
        firefighters_argument: '同意：目标不变，语气调整。',
        counselor_analysis: '双方达成新的内在协作模式。'
      } },
      { atMs: 32000, type: 'council_end', payload: { conclusion: '共识：保留追求成长，但将内在语言从“羞辱驱动”改为“支持驱动”。' } },
      { atMs: 35200, type: 'persona_switch', payload: { persona: 'manager', intensity: 0.43, reason: 'return_threshold' } },
      { atMs: 38200, type: 'assistant_message', payload: { persona: 'manager', emotionIntensity: 0.43, content: '你依然可以追求卓越，同时不再用伤害自己的方式前进。' } },
      { atMs: 41200, type: 'report_hint', payload: {
        core_beliefs: [
          { belief_id: 's1', content: '我必须完美才值得被爱', valence: -0.75, intensity: 8.9 },
          { belief_id: 's2', content: '出错意味着我很糟糕', valence: -0.67, intensity: 8.2 }
        ],
        persona_portraits: {
          exiles: '缩在角落里反复道歉的孩子。',
          firefighters: '手持鞭子的监工，逼迫自己不停向前。'
        },
        council_summary: '从“羞辱驱动”切换为“支持驱动”的成长模式。',
        emotion_trend: [0.8, 0.75, 0.69, 0.6, 0.51, 0.43],
        self_presence: 0.68,
        self_presence_trend: '持续提升中',
        counselor_note: '真正稳定的成长，不建立在自我攻击之上。'
      } },
      { atMs: 44800, type: 'narrative_chapter', payload: {
        title: '把鞭子换成灯',
        content: '她不再靠羞辱鞭策自己，而是学会在跌倒后先扶起自己。成长没有停止，只是终于变得温柔。',
        image_url: 'https://images.unsplash.com/photo-1503264116251-35a269479413?w=1200&q=80&auto=format&fit=crop'
      } },
      { atMs: 48600, type: 'social_hint', payload: {
        similarUsers: [
          {
            anonymous_id: 9933,
            similarity: 0.89,
            shared_beliefs: ['必须完美', '不能犯错'],
            exiles_summary: '对失败高度敏感，害怕让人失望。',
            firefighters_summary: '通过苛责与控制维持秩序。',
            can_chat: true,
            profile_kind: 'guide'
          }
        ]
      } }
    ]
  }
]

export const demoSocialSeed = {
  similarUsers: [
    {
      anonymous_id: 9901,
      similarity: 0.88,
      shared_beliefs: ['我值得被爱', '脆弱也是力量'],
      exiles_summary: '曾经害怕被忽视，现在学会了拥抱自己的孤独。',
      firefighters_summary: '用温柔的光照亮每一个角落。',
      can_chat: true,
      profile_kind: 'guide'
    },
    {
      anonymous_id: 9902,
      similarity: 0.82,
      shared_beliefs: ['真相值得追寻', '痛苦中藏着智慧'],
      exiles_summary: '在深海中寻找被遗忘的记忆碎片。',
      firefighters_summary: '用洞察力化解内心风暴。',
      can_chat: true,
      profile_kind: 'guide'
    },
    {
      anonymous_id: 9903,
      similarity: 0.79,
      shared_beliefs: ['成长需要边界', '慢下来也是前进'],
      exiles_summary: '总担心自己不够快，于是忽略了内心的疲惫。',
      firefighters_summary: '习惯在压力来临时先加速，再处理感受。'
    },
    {
      anonymous_id: 9904,
      similarity: 0.77,
      shared_beliefs: ['关系需要表达', '被理解很重要'],
      exiles_summary: '在冲突中容易退后，但内心很想被听见。',
      firefighters_summary: '会先沉默自保，之后才愿意重新靠近。'
    }
  ],
  myBottles: [
    {
      id: 'demo_bottle_1',
      persona_type: 'exiles',
      status: 'picked',
      created_at: new Date().toISOString(),
      message: '愿你在被理解前，先被自己抱住。'
    },
    {
      id: 'demo_bottle_2',
      persona_type: 'manager',
      status: 'drifting',
      created_at: new Date().toISOString(),
      message: '今天先把目标拆成三步，你已经走在路上。'
    },
    {
      id: 'demo_bottle_3',
      persona_type: 'witness',
      status: 'drifting',
      created_at: new Date().toISOString(),
      message: '当情绪经过身体时，先允许它停留 30 秒。'
    }
  ],
  pickedBottle: {
    id: 'demo_picked_1',
    persona_type: 'firefighters',
    persona_portrait: '我总在风暴前先把门锁紧，因为我怕再失去一次。',
    diary_text: '今晚我没有再命令自己坚强，而是允许自己安静地坐着。',
    message: '你不必每次都赢，也值得被爱。'
  }
}

export const demoAgentReplies = {
  default: [
    '我听到了，你在努力把一切维持住。',
    '你已经做得很多了，现在可以先慢一点。',
    '如果你愿意，我们可以把这件事拆成更小的下一步。',
    '先别急着证明自己，我们先确认你真正需要被保护的部分。',
    '你现在的反应不是问题，而是系统在用熟悉方式保护你。'
  ],
  warm: [
    '你并不孤单，我会在这里陪你把这段路走完。',
    '谢谢你愿意说出来，这本身就是很勇敢的动作。',
    '我们不需要一次解决全部，只要先让你此刻安全一点。',
    '你可以把重量放下来一点点，我会在这里接住这段感受。'
  ],
  deep: [
    '你此刻最害怕失去的，可能正是你最在意的价值。',
    '也许问题不在你不够好，而在你一直一个人扛。',
    '当你开始命名触发，你其实已经在夺回主动权。',
    '有时反复出现的痛点，不是弱点，而是未完成的求救信号。'
  ],
  rational: [
    '我们先区分事实、解释和情绪，再决定动作。',
    '高标准可以保留，但执行策略可以更温和。',
    '先做一个 15 分钟可执行动作，再决定是否扩大目标。',
    '我们把目标拆成“最低可行步”，让系统先恢复掌控感。'
  ]
}
