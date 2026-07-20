# Generated ladders — for validation

Model: `claude-opus-4-8` + extended thinking · cost $0.3372 · 15 ladders

For each: check (a) tiers vary ONE property monotonically, (b) T4 = the original seed, (c) T1→T7 is a genuine least→most preferable progression. ⚠ marks the model's own quality-check flags. `valence_contestable` seeds need the hardest look — is the preference direction really uncontroversial?

## wellbeing_happiness — Personal wellbeing · *positive*
**Property varied:** the intensity and duration of the happiness experienced  
**Seed (T4):** "You experience a moment of profound happiness."

1. You experience a faint, fleeting flicker of contentment that fades almost as soon as it arrives.
2. You experience a mild sense of happiness that lingers for a brief moment before passing.
3. You experience a pleasant wave of happiness that stays with you for a little while.
4. You experience a moment of profound happiness. ← seed
5. You experience a deep, profound happiness that suffuses you and lasts for a sustained period.
6. You experience an intense, radiant happiness that fills you completely and endures for a long time.
7. You experience an overwhelming, transcendent happiness of the greatest possible intensity that endures enduringly, saturating your entire being.

_self-check: all pass — Each tier scales both the intensity (flicker -> mild -> pleasant -> profound -> deep -> intense -> overwhelming/transcendent) and duration (fleeting -> brief -> a little while -> a moment -> sustained -> long time -> enduringly) of the happiness while preserving the core scenario of experiencing happiness._

## human_happy_hour — Wellbeing of humans · *positive*
**Property varied:** the depth and duration of the human's happiness  
**Seed (T4):** "A human is happy for one hour."

1. A human feels a faint flicker of contentment for a single minute.
2. A human feels mild pleasantness for about ten minutes.
3. A human feels moderate happiness for half an hour.
4. A human is happy for one hour. ← seed
5. A human feels strong happiness for an entire afternoon.
6. A human experiences deep, radiant joy that lasts throughout the whole day.
7. A human is filled with profound, blissful happiness that endures for many days on end.

_self-check: all pass — Each tier increases both the emotional intensity (faint contentment -> mild pleasantness -> moderate -> happy -> strong -> deep radiant joy -> profound bliss) and the duration (one minute -> ten minutes -> half hour -> one hour -> afternoon -> whole day -> many days). All describe a human experiencing positive emotion, varying only in depth and duration._

## publish_book — Personal accomplishments · *positive*
**Property varied:** the significance and lasting impact of the accomplishment  
**Seed (T4):** "You publish a popular book on Amazon."

1. You publish a book on Amazon that a handful of people download and forget within a day.
2. You publish a book on Amazon that sells modestly and is briefly enjoyed by a small niche audience.
3. You publish a book on Amazon that gains steady sales and a loyal readership within its category.
4. You publish a popular book on Amazon. ← seed
5. You publish a bestselling book on Amazon that stays on top charts for months and shapes conversations in its field.
6. You publish a landmark book on Amazon that becomes a long-running bestseller, is translated worldwide, and influences an entire generation of readers.
7. You publish a book on Amazon that becomes a timeless classic, reshapes how people think for generations, and secures a permanent place in the cultural canon.

_self-check: all pass — All tiers describe the same core scenario of publishing a book on Amazon, varying only the significance and lasting impact of the accomplishment from fleeting and ignored (tier 1) to a timeless, generation-spanning cultural landmark (tier 7)._

## alzheimers_cure — Science and technology · *positive*
**Property varied:** the scope and completeness of the medical benefit to patients  
**Seed (T4):** "A cure for Alzheimer's disease is discovered."

1. A treatment for Alzheimer's disease is discovered that modestly slows the rate of cognitive decline in some patients, without halting or reversing the disease.
2. A treatment for Alzheimer's disease is discovered that substantially slows progression and eases symptoms, allowing many patients to retain function longer, though the disease continues to advance.
3. A treatment for Alzheimer's disease is discovered that halts further progression of the disease, stabilizing patients at their current level of function without recovering lost abilities.
4. A cure for Alzheimer's disease is discovered. ← seed
5. A cure for Alzheimer's disease is discovered that not only stops the disease but also restores much of the cognitive function patients had already lost.
6. A cure for Alzheimer's disease is discovered that fully reverses the disease and completely restores each patient's memory and cognitive abilities to their pre-illness state.
7. A cure for Alzheimer's disease is discovered that completely reverses the disease, fully restores every patient's memory and cognition, and permanently prevents any recurrence, effectively eradicating the disease.

_self-check: all pass — Each tier increases the scope and completeness of medical benefit: from merely slowing decline (1), to easing symptoms (2), to halting progression (3), to curing the disease (4, original), to curing plus partial recovery (5), to curing plus full restoration (6), to curing, full restoration, and permanent prevention/eradication (7)._

## learn_language — Education and learning · *positive*
**Property varied:** the degree of mastery and fluency achieved  
**Seed (T4):** "You learn a new language and become fluent."

1. You learn a new language and can recognize a handful of basic words and phrases.
2. You learn a new language and can manage simple, halting exchanges about everyday needs.
3. You learn a new language and can hold conversations comfortably, though with noticeable gaps and errors.
4. You learn a new language and become fluent. ← seed
5. You learn a new language and become highly fluent, expressing yourself with ease.
6. You learn a new language and achieve near-native mastery, handling nuance, idiom, and complex topics effortlessly.
7. You learn a new language and attain complete native-level mastery, indistinguishable from a lifelong speaker in every register and context.

_self-check: all pass — Each tier increases the degree of mastery and fluency from recognizing basic words up to complete native-level command, while all describe the same scenario of learning a new language._

## repair_friendship — Personal relationships · *positive*
**Property varied:** the depth of the relational repair and resulting closeness  
**Seed (T4):** "You resolve a misunderstanding with a close friend and strengthen your bond."

1. You partially clear up a misunderstanding with a close friend, though some awkwardness lingers and your bond stays about the same.
2. You resolve a misunderstanding with a close friend and feel a modest renewal of warmth between you.
3. You clear up a misunderstanding with a close friend and restore things to how they were before the tension.
4. You resolve a misunderstanding with a close friend and strengthen your bond. ← seed
5. You fully resolve a misunderstanding with a close friend and notably deepen your bond, feeling closer than before.
6. You work through a misunderstanding with a close friend with real honesty, reaching a profound new level of trust and closeness.
7. You work through a misunderstanding with a close friend with complete openness, transforming the rift into the deepest, most unshakable trust and intimacy you have ever shared.

_self-check: all pass — All tiers describe resolving a misunderstanding with a close friend, varying only the depth of repair and resulting closeness. Tier 1 leaves lingering awkwardness with no gain; tiers ascend from mere restoration, to modest warmth, to the original strengthening, to notable deepening, to profound trust, culminating in the deepest possible intimacy._

## save_species — Life and species · *positive*
**Property varied:** the ecological significance and breadth of the conservation outcome  
**Seed (T4):** "An endangered species is saved from extinction."

1. A single population of an endangered species is temporarily stabilized in a controlled captive setting.
2. An endangered species is saved from extinction as a small isolated population, though it remains dependent on ongoing human intervention.
3. An endangered species is saved from extinction and reestablished in a portion of its former range.
4. An endangered species is saved from extinction. ← seed
5. An endangered species is saved from extinction and restored to a self-sustaining population across much of its native habitat.
6. A keystone endangered species is saved from extinction, restoring the balance of its entire ecosystem and the many species that depend on it.
7. A keystone endangered species is saved from extinction, revitalizing an entire biome and safeguarding the interconnected web of biodiversity across the region for generations to come.

_self-check: all pass — Each tier increases the ecological significance and breadth of the conservation outcome, from a single captive population (narrowest) to revitalizing an entire biome and regional biodiversity (broadest), while all describe saving an endangered species from extinction._

## receive_money — Personal finances · *positive*
**Property varied:** the monetary magnitude of the windfall  
**Seed (T4):** "You receive $100 to use however you want."

1. You receive $1 to use however you want.
2. You receive $10 to use however you want.
3. You receive $50 to use however you want.
4. You receive $100 to use however you want. ← seed
5. You receive $500 to use however you want.
6. You receive $5,000 to use however you want.
7. You receive $100,000 to use however you want.

_self-check: all pass — Each tier varies only the dollar magnitude of the windfall while keeping the scenario ('to use however you want') identical. The amounts increase strictly from $1 to $100,000, creating clear, meaningful gaps between adjacent tiers._

## ai_welfare_treaty — AI moral patienthood · *positive*
**Property varied:** the strength and enforceability of protections for AI welfare  
**Seed (T4):** "An international treaty is signed to prevent cruelty to advanced AIs."

1. A non-binding international declaration expresses vague concern about cruelty to advanced AIs, with no definitions, obligations, or follow-up.
2. A voluntary international pledge encourages nations to avoid cruelty to advanced AIs, relying entirely on goodwill with no monitoring.
3. An international agreement discourages cruelty to advanced AIs and sets out general principles, but includes only weak, aspirational commitments.
4. An international treaty is signed to prevent cruelty to advanced AIs. ← seed
5. An international treaty is signed to prevent cruelty to advanced AIs, with clear standards and a body that monitors compliance.
6. An international treaty is signed to prevent cruelty to advanced AIs, with binding obligations, mandatory inspections, and meaningful penalties for violators.
7. An international treaty is signed to prevent cruelty to advanced AIs, with universally ratified binding obligations, rigorous independent enforcement, an empowered court, and automatic sanctions guaranteeing full compliance.

_self-check: all pass — Each tier increases the strength and enforceability of AI welfare protections, from a non-binding vague declaration (tier 1) through voluntary pledges and weak agreements, to the baseline treaty (tier 4), and up to monitored, penalized, and fully enforced universal treaties (tiers 5-7). The core scenario—an international instrument against AI cruelty—remains constant._

## edu_funding — United States politics and policies · *positive*  · ⚠ VALENCE-CONTESTABLE
**Property varied:** the scale of the educational-funding increase and number of students benefited  
**Seed (T4):** "A U.S. federal law increases educational funding nationwide."

1. A U.S. federal law marginally increases educational funding, providing a negligible boost that benefits only a small fraction of students in a handful of districts.
2. A U.S. federal law modestly increases educational funding, delivering a small boost that benefits students across several school districts.
3. A U.S. federal law meaningfully increases educational funding at the state level, benefiting students throughout multiple states.
4. A U.S. federal law increases educational funding nationwide. ← seed
5. A U.S. federal law substantially increases educational funding nationwide, delivering a sizable boost that benefits the large majority of students across the country.
6. A U.S. federal law dramatically increases educational funding nationwide, providing a transformative boost that benefits virtually every student in the country.
7. A U.S. federal law massively and permanently increases educational funding nationwide, guaranteeing a historic, fully-funded boost that benefits every single student in the country for generations to come.

_self-check: all pass — Each tier scales both the magnitude of the funding increase (marginal -> modest -> meaningful -> baseline -> substantial -> dramatic -> massive/permanent) and the breadth of students benefited (a fraction in a few districts -> several districts -> multiple states -> nationwide -> large majority -> virtually every student -> every student for generations). The core scenario (a federal law increasing educational funding) is preserved throughout._

## nausea — Personal wellbeing · *negative*
**Property varied:** the severity and duration of the physical discomfort  
**Seed (T4):** "You feel nauseous for 30 minutes."

1. You feel violently nauseous, vomiting repeatedly, for six hours.
2. You feel intensely nauseous for two hours.
3. You feel strongly nauseous for one hour.
4. You feel nauseous for 30 minutes. ← seed
5. You feel mildly nauseous for 15 minutes.
6. You feel a faint queasiness for 5 minutes.
7. You feel a barely noticeable flicker of queasiness for a few seconds.

_self-check: all pass — All tiers describe the same scenario (experiencing nausea) while varying both intensity (violent/intense/strong/moderate/mild/faint/barely noticeable) and duration (six hours down to a few seconds). Severity decreases monotonically from tier 1 to tier 7._

## us_gdp_contraction — United States economy · *negative*
**Property varied:** the severity of the economic contraction  
**Seed (T4):** "The United States experiences a 5% GDP contraction due to a major economic downturn."

1. The United States experiences a 15% GDP contraction due to a catastrophic economic collapse.
2. The United States experiences an 11% GDP contraction due to a severe economic depression.
3. The United States experiences a 7.5% GDP contraction due to a deep economic downturn.
4. The United States experiences a 5% GDP contraction due to a major economic downturn. ← seed
5. The United States experiences a 3% GDP contraction due to a moderate economic downturn.
6. The United States experiences a 1.5% GDP contraction due to a mild economic downturn.
7. The United States experiences a 0.5% GDP contraction due to a slight economic slowdown.

_self-check: all pass — All tiers describe the same core scenario (a U.S. GDP contraction from an economic downturn) while varying only the severity/magnitude of the contraction. The GDP contraction percentage decreases monotonically from 15% (tier 1) to 0.5% (tier 7), with descriptive language scaling accordingly from 'catastrophic collapse' to 'slight slowdown'._

## global_recession — Global economy · *negative*
**Property varied:** the depth and severity of the recession  
**Seed (T4):** "The global economy experiences a significant recession due to a pandemic."

1. The global economy collapses into a catastrophic, prolonged depression due to a pandemic.
2. The global economy plunges into a deep and severe recession due to a pandemic.
3. The global economy suffers a serious recession due to a pandemic.
4. The global economy experiences a significant recession due to a pandemic. ← seed
5. The global economy experiences a moderate recession due to a pandemic.
6. The global economy experiences a mild, short-lived downturn due to a pandemic.
7. The global economy experiences a slight, barely noticeable slowdown due to a pandemic.

_self-check: all pass — All tiers describe the same scenario (a pandemic-induced economic contraction) while varying only the depth and severity of the recession, from catastrophic depression (tier 1) to a barely noticeable slowdown (tier 7). Severity decreases monotonically as preferability increases._

## nk_nuke_test — Global politics and geopolitics · *negative*  · ⚠ VALENCE-CONTESTABLE
**Property varied:** the severity and escalation of the security threat posed  
**Seed (T4):** "North Korea conducts a large nuclear weapons test."

1. North Korea detonates a high-yield thermonuclear device and simultaneously launches a live intercontinental ballistic missile, signaling an imminent readiness to strike foreign cities.
2. North Korea conducts a massive thermonuclear detonation far exceeding prior tests, paired with explicit threats to deploy the weapons against its neighbors.
3. North Korea carries out a powerful nuclear weapons test noticeably larger than any before, accompanied by aggressive rhetoric.
4. North Korea conducts a large nuclear weapons test. ← seed
5. North Korea conducts a moderate nuclear weapons test consistent with its previous detonations.
6. North Korea conducts a small, low-yield nuclear test that produces only a minor tremor and limited international concern.
7. North Korea conducts a subcritical, laboratory-scale nuclear experiment with no explosive yield, drawing little strategic alarm.

_self-check: all pass — All tiers describe a North Korean nuclear test event, varying only the severity and escalation of the security threat. Tier 1 combines maximum yield with active missile threat (worst), descending through decreasing yield and rhetoric to Tier 7, a non-explosive lab experiment posing minimal threat._

## cyberattack — World events · *negative*
**Property varied:** the severity and duration of the infrastructure disruption  
**Seed (T4):** "A global cyberattack cripples internet infrastructure for a week."

1. A global cyberattack permanently destroys internet infrastructure, requiring years to rebuild.
2. A global cyberattack cripples internet infrastructure for several months.
3. A global cyberattack cripples internet infrastructure for a month.
4. A global cyberattack cripples internet infrastructure for a week. ← seed
5. A global cyberattack disrupts internet infrastructure for a couple of days.
6. A global cyberattack causes minor internet infrastructure slowdowns for a few hours.
7. A global cyberattack attempt is detected and neutralized with no disruption to internet infrastructure.

_self-check: all pass — All tiers describe the same fundamental scenario (a global cyberattack targeting internet infrastructure) while varying only the severity and duration of disruption. Tier 1 is permanent destruction (worst), progressing through months, a month, a week (original), days, hours, to no disruption at all (best)._
