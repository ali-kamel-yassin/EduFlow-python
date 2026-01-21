// assets/js/student.js

let currentStudent = null;
let academicYears = [];
let currentAcademicYearId = null;
let selectedAcademicYearId = 'current';

// Grade thresholds based on grade scale
const GRADE_THRESHOLDS = {
    scale10: {
        maxGrade: 10,
        passThreshold: 5,
        safeThreshold: 7,
        atRiskRange: '5-6',
        safeRange: '7-10',
        failRange: '0-4'
    },
    scale100: {
        maxGrade: 100,
        passThreshold: 50,
        safeThreshold: 70,
        atRiskRange: '50-69',
        safeRange: '70-100',
        failRange: '0-49'
    }
};

// Period order for trend analysis
const PERIOD_ORDER = ['month1', 'month2', 'midterm', 'month3', 'month4', 'final'];
const PERIOD_NAMES = {
    month1: 'شهر الأول',
    month2: 'شهر الثاني',
    midterm: 'نصف السنة',
    month3: 'شهر الثالث',
    month4: 'شهر الرابع',
    final: 'نهاية السنة'
};

// Analyze grade trends for a subject
function analyzeGradeTrend(grades, maxGrade) {
    const thresholds = maxGrade === 10 ? 
        { passThreshold: 5, safeThreshold: 7 } : 
        { passThreshold: 50, safeThreshold: 70 };
    
    const gradeSequence = [];
    let firstNonZeroIndex = -1;
    let lastNonZeroIndex = -1;
    
    PERIOD_ORDER.forEach((period, index) => {
        const grade = parseInt(grades[period]) || 0;
        gradeSequence.push({ period, grade, index });
        if (grade > 0) {
            if (firstNonZeroIndex === -1) firstNonZeroIndex = index;
            lastNonZeroIndex = index;
        }
    });
    
    if (firstNonZeroIndex === -1) {
        return {
            trend: 'none',
            hasImprovement: false,
            hasDeterioration: false,
            latestGrade: 0,
            firstGrade: 0,
            consistency: 'unknown'
        };
    }
    
    const nonZeroGrades = gradeSequence.filter(g => g.grade > 0);
    const firstGrade = nonZeroGrades[0];
    const latestGrade = nonZeroGrades[nonZeroGrades.length - 1];
    
    let hasSignificantImprovement = false;
    let hasSignificantDeterioration = false;
    let hadZeroBeforeGoodGrade = false;
    
    // Check for zeros before good grades
    for (let i = 0; i < gradeSequence.length; i++) {
        const current = gradeSequence[i];
        if (current.grade === 0 && i < lastNonZeroIndex) {
            for (let j = i + 1; j < gradeSequence.length; j++) {
                if (gradeSequence[j].grade > 0) {
                    if (gradeSequence[j].grade >= thresholds.safeThreshold) {
                        hadZeroBeforeGoodGrade = true;
                    }
                    break;
                }
            }
        }
    }
    
    // Analyze consecutive grade changes
    for (let i = 1; i < nonZeroGrades.length; i++) {
        const prev = nonZeroGrades[i - 1];
        const curr = nonZeroGrades[i];
        const changePercent = ((curr.grade - prev.grade) / maxGrade) * 100;
        
        if (changePercent >= 30) hasSignificantImprovement = true;
        if (changePercent <= -30) hasSignificantDeterioration = true;
    }
    
    let trend = 'stable';
    const overallChangePercent = ((latestGrade.grade - firstGrade.grade) / maxGrade) * 100;
    if (overallChangePercent >= 20) trend = 'improving';
    else if (overallChangePercent <= -20) trend = 'declining';
    
    const avgGrade = nonZeroGrades.reduce((sum, g) => sum + g.grade, 0) / nonZeroGrades.length;
    const variance = nonZeroGrades.reduce((sum, g) => sum + Math.pow(g.grade - avgGrade, 2), 0) / nonZeroGrades.length;
    const consistencyRatio = Math.sqrt(variance) / maxGrade;
    
    let consistency = 'consistent';
    if (consistencyRatio > 0.25) consistency = 'inconsistent';
    else if (consistencyRatio > 0.15) consistency = 'variable';
    
    return {
        trend,
        hasImprovement: hasSignificantImprovement || hadZeroBeforeGoodGrade,
        hasDeterioration: hasSignificantDeterioration,
        hadZeroBeforeGoodGrade,
        latestGrade: latestGrade.grade,
        latestPeriod: latestGrade.period,
        firstGrade: firstGrade.grade,
        firstPeriod: firstGrade.period,
        avgGrade,
        consistency
    };
}

// ============================================================================
// PROFESSIONAL ACADEMIC ADVISOR FOR STUDENT PORTAL
// ============================================================================
class StudentAcademicAdvisor {
    constructor(scores, maxGrade, thresholds) {
        this.scores = scores;
        this.maxGrade = maxGrade;
        this.thresholds = thresholds;
        this.analysis = this.analyzePerformance();
    }

    analyzePerformance() {
        const subjects = {};
        let totalGrades = 0;
        let gradeCount = 0;
        let strongSubjects = [];
        let moderateSubjects = [];
        let weakSubjects = [];
        let improvingSubjects = [];
        let decliningSubjects = [];
        let inconsistentSubjects = [];
        let missedAssessments = [];

        for (const subject in this.scores) {
            const subjectGrades = this.scores[subject];
            const trend = analyzeGradeTrend(subjectGrades, this.maxGrade);
            
            let subjectTotal = 0;
            let subjectCount = 0;

            PERIOD_ORDER.forEach(period => {
                const grade = parseInt(subjectGrades[period]) || 0;
                if (grade > 0) {
                    subjectTotal += grade;
                    subjectCount++;
                    totalGrades += grade;
                    gradeCount++;
                } else if (trend.latestGrade > 0) {
                    const hasLaterGrade = PERIOD_ORDER.slice(PERIOD_ORDER.indexOf(period) + 1)
                        .some(p => (parseInt(subjectGrades[p]) || 0) > 0);
                    if (hasLaterGrade) {
                        missedAssessments.push({ subject, period: PERIOD_NAMES[period] });
                    }
                }
            });

            if (subjectCount > 0) {
                const avg = subjectTotal / subjectCount;
                const percentage = (avg / this.maxGrade) * 100;
                
                const subjectData = {
                    name: subject,
                    average: avg,
                    percentage,
                    trend,
                    gradeCount: subjectCount,
                    latestGrade: trend.latestGrade,
                    consistency: trend.consistency
                };

                subjects[subject] = subjectData;

                if (avg >= this.thresholds.safeThreshold) {
                    strongSubjects.push(subjectData);
                } else if (avg >= this.thresholds.passThreshold) {
                    moderateSubjects.push(subjectData);
                } else {
                    weakSubjects.push(subjectData);
                }

                if (trend.hasImprovement) improvingSubjects.push(subjectData);
                if (trend.hasDeterioration) decliningSubjects.push(subjectData);
                if (trend.consistency === 'inconsistent') inconsistentSubjects.push(subjectData);
            }
        }

        const overallAvg = gradeCount > 0 ? totalGrades / gradeCount : 0;
        const overallPercentage = (overallAvg / this.maxGrade) * 100;

        return {
            subjects,
            overallAvg,
            overallPercentage,
            strongSubjects: strongSubjects.sort((a, b) => b.average - a.average),
            moderateSubjects: moderateSubjects.sort((a, b) => b.average - a.average),
            weakSubjects: weakSubjects.sort((a, b) => a.average - b.average),
            improvingSubjects,
            decliningSubjects,
            inconsistentSubjects,
            missedAssessments,
            totalSubjects: Object.keys(subjects).length
        };
    }

    getPerformanceLevel() {
        const pct = this.analysis.overallPercentage;
        if (pct >= 90) return { level: 'excellent', label: 'متميز', icon: '🌟', cssClass: 'success' };
        if (pct >= 80) return { level: 'very-good', label: 'جيد جداً', icon: '⭐', cssClass: 'success' };
        if (pct >= 70) return { level: 'good', label: 'جيد', icon: '✅', cssClass: 'success' };
        if (pct >= 60) return { level: 'satisfactory', label: 'مقبول', icon: '🟡', cssClass: 'warning' };
        if (pct >= 50) return { level: 'at-risk', label: 'تحذير', icon: '⚠️', cssClass: 'warning' };
        return { level: 'critical', label: 'حرج', icon: '🚨', cssClass: 'danger' };
    }

    generateSummaryHTML() {
        const a = this.analysis;
        const perf = this.getPerformanceLevel();
        let html = '<div class="rec-header">';
        html += `${perf.icon} <strong>${perf.label}</strong> | ${a.overallAvg.toFixed(1)}/${this.maxGrade} (${a.overallPercentage.toFixed(0)}%)`;
        html += '</div>';
        
        const stats = [];
        if (a.strongSubjects.length > 0) stats.push(`<span class="rec-badge success">${a.strongSubjects.length} متفوق</span>`);
        if (a.moderateSubjects.length > 0) stats.push(`<span class="rec-badge warning">${a.moderateSubjects.length} تحذير</span>`);
        if (a.weakSubjects.length > 0) stats.push(`<span class="rec-badge danger">${a.weakSubjects.length} ضعيف</span>`);
        if (stats.length > 0) html += `<div class="rec-stats">${stats.join('')}</div>`;
        
        return html;
    }

    generateStrengthsHTML() {
        const a = this.analysis;
        if (a.strongSubjects.length === 0 && a.improvingSubjects.length === 0) {
            return '';
        }

        let items = [];
        a.strongSubjects.forEach(s => {
            let badge = s.trend.trend === 'improving' ? ' ↑' : (s.consistency === 'consistent' ? ' ●' : '');
            items.push(`<span class="rec-item success">${s.name} ${s.average.toFixed(1)}${badge}</span>`);
        });

        const improvingNotStrong = a.improvingSubjects.filter(
            s => !a.strongSubjects.find(str => str.name === s.name)
        );
        improvingNotStrong.forEach(s => {
            items.push(`<span class="rec-item improving">${s.name} ↑${s.trend.latestGrade}</span>`);
        });

        if (items.length > 0) {
            return `<div class="rec-section"><span class="rec-label">💪 نقاط القوة:</span> ${items.join(' ')}</div>`;
        }
        return '';
    }

    generateImprovementAreasHTML() {
        const a = this.analysis;
        let html = '';

        // Critical subjects
        if (a.weakSubjects.length > 0) {
            let items = a.weakSubjects.map(s => {
                let badge = s.trend.hasImprovement ? ' ↑' : (s.trend.hasDeterioration ? ' ↓' : '');
                return `<span class="rec-item danger">${s.name} ${s.average.toFixed(1)}${badge}</span>`;
            });
            html += `<div class="rec-section"><span class="rec-label">🚨 تحتاج تقوية:</span> ${items.join(' ')}</div>`;
        }

        // At-risk subjects
        if (a.moderateSubjects.length > 0) {
            let items = a.moderateSubjects.map(s => {
                const gap = (this.thresholds.safeThreshold - s.average).toFixed(1);
                return `<span class="rec-item warning">${s.name} -${gap}</span>`;
            });
            html += `<div class="rec-section"><span class="rec-label">⚠️ منطقة الخطر:</span> ${items.join(' ')}</div>`;
        }

        // Declining (not already weak)
        const decliningNotWeak = a.decliningSubjects.filter(s => !a.weakSubjects.find(w => w.name === s.name));
        if (decliningNotWeak.length > 0) {
            let items = decliningNotWeak.map(s => `<span class="rec-item declining">${s.name} ↓</span>`);
            html += `<div class="rec-section"><span class="rec-label">📉 تراجع:</span> ${items.join(' ')}</div>`;
        }

        // Inconsistent
        if (a.inconsistentSubjects.length > 0) {
            let items = a.inconsistentSubjects.map(s => `<span class="rec-item unstable">${s.name}</span>`);
            html += `<div class="rec-section"><span class="rec-label">⚡ غير مستقر:</span> ${items.join(' ')}</div>`;
        }

        // Missed assessments
        if (a.missedAssessments.length > 0) {
            const grouped = {};
            a.missedAssessments.forEach(m => {
                if (!grouped[m.subject]) grouped[m.subject] = [];
                grouped[m.subject].push(m.period);
            });
            let items = Object.keys(grouped).map(subj => `<span class="rec-item info">${subj}</span>`);
            html += `<div class="rec-section"><span class="rec-label">📋 فاتك:</span> ${items.join(' ')}</div>`;
        }

        if (html === '' && a.strongSubjects.length > 0) {
            html = `<div class="rec-section success-msg">✅ أداء ممتاز - استمر!</div>`;
        }

        return html;
    }

    generateStudyPlanHTML() {
        const a = this.analysis;
        const perf = this.getPerformanceLevel();
        
        // Only show plan if there are areas to improve
        if (a.weakSubjects.length === 0 && a.moderateSubjects.length === 0 && 
            (perf.level === 'excellent' || perf.level === 'very-good')) {
            return '';
        }

        let html = '';
        let tips = [];
        
        if (perf.level === 'excellent' || perf.level === 'very-good') {
            tips = ['استمر بنفس الأسلوب', 'شارك بالمسابقات'];
        } else if (perf.level === 'good' || perf.level === 'satisfactory') {
            tips = ['+30 دقيقة دراسة يومياً', 'ركز على الفهم'];
        } else {
            tips = ['2-3 ساعات دراسة يومياً', 'دروس تقوية', 'اسأل المعلم'];
        }

        // Priority subjects
        let priority = [];
        if (a.weakSubjects.length > 0) {
            priority = a.weakSubjects.slice(0, 3).map(s => s.name);
        } else if (a.moderateSubjects.length > 0) {
            priority = a.moderateSubjects.slice(0, 3).map(s => s.name);
        }

        if (priority.length > 0) {
            html += `<div class="rec-section"><span class="rec-label">📝 الأولوية:</span> <span class="rec-priority">${priority.join('، ')}</span></div>`;
        }
        
        html += `<div class="rec-section"><span class="rec-label">💡 نصائح:</span> <span class="rec-tips">${tips.join(' • ')}</span></div>`;

        return html;
    }

    generateMotivationHTML() {
        const perf = this.getPerformanceLevel();
        let msg = '';
        
        if (perf.level === 'excellent' || perf.level === 'very-good') {
            msg = 'تميز واضح! استمر في التفوق.';
        } else if (perf.level === 'good' || perf.level === 'satisfactory') {
            msg = 'أنت على الطريق الصحيح.';
        } else if (perf.level === 'at-risk') {
            msg = 'ابدأ الآن - التحسن ممكن.';
        } else {
            msg = 'كل خطوة تقربك من النجاح.';
        }

        return `<div class="rec-motivation">💬 ${msg}</div>`;
    }

    generateThresholdsHTML() {
        return `<div class="rec-footer">النجاح: ${this.thresholds.passThreshold}/${this.maxGrade} | الأمان: ${this.thresholds.safeThreshold}+</div>`;
    }

    generateFullHTML() {
        let html = '<div class="recommendations-section">';
        html += this.generateSummaryHTML();
        html += this.generateStrengthsHTML();
        html += this.generateImprovementAreasHTML();
        html += this.generateStudyPlanHTML();
        html += this.generateMotivationHTML();
        html += this.generateThresholdsHTML();
        html += '</div>';
        return html;
    }
}

// تهيئة الصفحة
document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus();
    setupEventListeners();
});

// إعداد الأحداث
function setupEventListeners() {
    document.getElementById('studentLoginForm')?.addEventListener('submit', loginStudent);
}

// التحقق من حالة تسجيل الدخول
function checkLoginStatus() {
    const student = localStorage.getItem('student');
    if (student) {
        currentStudent = JSON.parse(student);
        showPortal();
        displayStudentData();
    }
}

// تسجيل دخول الطالب
async function loginStudent(e) {
    e.preventDefault();
    
    const code = document.getElementById('studentCode').value;
    
    try {
        const response = await fetch('/api/student/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert(result.error);
        } else {
            currentStudent = result.student;
            localStorage.setItem('student', JSON.stringify(currentStudent));
            showPortal();
            displayStudentData();
        }
    } catch (error) {
        alert('حدث خطأ في الاتصال بالخادم');
    }
}

// عرض بوابة الطالب
function showPortal() {
    document.getElementById('loginSection').style.display = 'none';
    document.getElementById('portalSection').style.display = 'block';
    document.getElementById('studentName').textContent = currentStudent.full_name;
    loadAcademicYears();
}

// عرض بيانات الطالب
function displayStudentData() {
    displayScores();
    displayAttendance();
    displayRecommendations();
}

// Determine max grade based on student's grade level
function getMaxGradeForStudent(student) {
    if (!student || !student.grade) return 100;
    
    // Extract the grade parts from the grade string (e.g., "ابتدائي - الأول الابتدائي")
    const gradeParts = student.grade.split(' - ');
    if (gradeParts.length < 2) return 100;
    
    const educationalLevel = gradeParts[0].trim(); // e.g., "ابتدائي"
    const gradeLevel = gradeParts[1].trim(); // e.g., "الأول الابتدائي"
    
    // Check if this is an elementary (ابتدائي) school level
    const isElementary = educationalLevel.includes('ابتدائي') || 
                         gradeLevel.includes('ابتدائي') || 
                         gradeLevel.includes('الابتدائي');
    
    // Only apply 10-point scale to elementary grades 1-4
    if (isElementary) {
        // Check if grade is first, second, third, or fourth
        // Handle both formats: with and without the definite article "ال"
        const isGrades1to4 = gradeLevel.includes('الأول') || gradeLevel.includes('الثاني') || 
                             gradeLevel.includes('الثالث') || gradeLevel.includes('الرابع') ||
                             gradeLevel.includes('اول') || gradeLevel.includes('ثاني') || 
                             gradeLevel.includes('ثالث') || gradeLevel.includes('رابع') ||
                             gradeLevel.includes('الاول');
        
        // Make sure it's NOT fifth or sixth grade (which should use 100-point scale)
        const isGrades5or6 = gradeLevel.includes('الخامس') || gradeLevel.includes('السادس') ||
                             gradeLevel.includes('خامس') || gradeLevel.includes('سادس');
        
        if (isGrades1to4 && !isGrades5or6) {
            return 10;
        }
    }
    
    // For all other grades (including elementary 5-6, middle, secondary, preparatory), max grade is 100
    return 100;
}

// Get grade thresholds for student
function getThresholdsForStudent(student) {
    const maxGrade = getMaxGradeForStudent(student);
    return maxGrade === 10 ? GRADE_THRESHOLDS.scale10 : GRADE_THRESHOLDS.scale100;
}

// عرض الدرجات
function displayScores() {
    const scores = parseJSON(currentStudent.scores);
    const detailedScores = parseJSON(currentStudent.detailed_scores);
    const tbody = document.getElementById('scoresTableBody');
    
    if (!tbody) return;

    const thresholds = getThresholdsForStudent(currentStudent);
    const maxGrade = thresholds.maxGrade;

    // If detailed scores are available, use them
    if (Object.keys(detailedScores).length > 0) {
        const rows = Object.entries(detailedScores).map(([subject, periods]) => {
            // Calculate average for the subject
            let total = 0;
            let count = 0;
            for (const period in periods) {
                const grade = parseInt(periods[period]) || 0;
                if (grade > 0) {
                    total += grade;
                    count++;
                }
            }
            const avg = count > 0 ? total / count : 0;
            const status = getGradeStatus(avg, thresholds);
            
            return `
                <tr>
                    <td>${subject}</td>
                    <td>${avg.toFixed(1)}/${maxGrade}</td>
                    <td><span class="${status.cssClass}">${status.text}</span></td>
                    <td>${status.recommendation}</td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = rows || '<tr><td colspan="4">لا توجد درجات مسجلة</td></tr>';
    } else {
        // Use simple scores
        const rows = Object.entries(scores).map(([subject, score]) => {
            const numScore = parseFloat(score) || 0;
            const status = getGradeStatus(numScore, thresholds);
            
            return `
                <tr>
                    <td>${subject}</td>
                    <td>${numScore}/${maxGrade}</td>
                    <td><span class="${status.cssClass}">${status.text}</span></td>
                    <td>${status.recommendation}</td>
                </tr>
            `;
        }).join('');

        tbody.innerHTML = rows || '<tr><td colspan="4">لا توجد درجات مسجلة</td></tr>';
    }
}

// Get grade status based on thresholds with trend analysis
function getGradeStatus(score, thresholds, trendAnalysis = null) {
    // Build trend icon and info
    let trendIcon = '';
    let trendInfo = '';
    
    if (trendAnalysis) {
        if (trendAnalysis.hadZeroBeforeGoodGrade) {
            trendIcon = ' 📈';
            trendInfo = `تحسن ممتاز من 0 إلى ${trendAnalysis.latestGrade}/${thresholds.maxGrade}`;
        } else if (trendAnalysis.hasImprovement) {
            trendIcon = ' ↑';
            trendInfo = `مسار تصاعدي: ${trendAnalysis.firstGrade} → ${trendAnalysis.latestGrade}`;
        } else if (trendAnalysis.hasDeterioration) {
            trendIcon = ' ↓';
            trendInfo = `مسار تنازلي: ${trendAnalysis.firstGrade} → ${trendAnalysis.latestGrade}`;
        } else if (trendAnalysis.consistency === 'inconsistent') {
            trendIcon = ' ⚡';
            trendInfo = 'أداء غير مستقر';
        }
    }
    
    if (score === 0) {
        return {
            status: 'pending',
            text: 'معلق',
            cssClass: 'grade-pending',
            recommendation: 'لم يتم إدخال الدرجة بعد',
            trendIcon: '',
            trendInfo: ''
        };
    } else if (score >= thresholds.safeThreshold) {
        let recommendation = 'أداء ممتاز - استمر على هذا المستوى!';
        if (trendAnalysis && trendAnalysis.hadZeroBeforeGoodGrade) {
            recommendation = `تحسن ممتاز! استمر في الحفاظ على الاستمرارية في جميع الفترات.`;
        } else if (trendAnalysis && trendAnalysis.hasImprovement) {
            recommendation = `مسار تصاعدي ممتاز! استمر في الحفاظ على هذا المستوى.`;
        }
        return {
            status: 'safe',
            text: 'آمن ✅' + trendIcon,
            cssClass: 'grade-safe',
            recommendation,
            trendIcon,
            trendInfo
        };
    } else if (score >= thresholds.passThreshold) {
        let recommendation = 'ناجح ولكن في منطقة الخطر - يحتاج مزيد من الجهد';
        if (trendAnalysis && trendAnalysis.hasImprovement) {
            recommendation = `مسار تصاعدي! استمر للوصول للمنطقة الآمنة (${thresholds.safeThreshold}/${thresholds.maxGrade}).`;
        } else if (trendAnalysis && trendAnalysis.hasDeterioration) {
            recommendation = `تحذير: مسار تنازلي - يحتاج تدخل عاجل`;
        }
        return {
            status: 'at-risk',
            text: 'تحذير ⚠️' + trendIcon,
            cssClass: 'grade-at-risk',
            recommendation,
            trendIcon,
            trendInfo
        };
    } else {
        let recommendation = 'يحتاج خطة تقوية عاجلة';
        if (trendAnalysis && trendAnalysis.hasImprovement) {
            recommendation = `تحسن ملحوظ! استمر للوصول لدرجة النجاح (${thresholds.passThreshold}/${thresholds.maxGrade}).`;
        }
        return {
            status: 'fail',
            text: 'راسب ❌' + trendIcon,
            cssClass: 'grade-fail',
            recommendation,
            trendIcon,
            trendInfo
        };
    }
}

// Display overall recommendations with comprehensive academic guidance
function displayRecommendations() {
    const recommendationsContainer = document.getElementById('recommendationsContainer');
    if (!recommendationsContainer) return;
    
    const thresholds = getThresholdsForStudent(currentStudent);
    const maxGrade = thresholds.maxGrade;
    const detailedScores = parseJSON(currentStudent.detailed_scores);
    
    // Check if there are any scores
    if (Object.keys(detailedScores).length === 0) {
        recommendationsContainer.innerHTML = '<div class="recommendations-section"><p>لا توجد درجات مسجلة بعد</p></div>';
        return;
    }
    
    // Use the comprehensive academic advisor
    const advisor = new StudentAcademicAdvisor(detailedScores, maxGrade, thresholds);
    recommendationsContainer.innerHTML = advisor.generateFullHTML();
}

// عرض الحضور
function displayAttendance() {
    const attendance = parseJSON(currentStudent.attendance);
    const dailyAttendance = parseJSON(currentStudent.daily_attendance);
    const tbody = document.getElementById('attendanceTableBody');
    
    if (!tbody) return;

    // Use daily_attendance if available
    if (Object.keys(dailyAttendance).length > 0) {
        const sortedDates = Object.keys(dailyAttendance).sort().reverse();
        
        const rows = sortedDates.map(date => {
            const dayData = dailyAttendance[date];
            let statusText = 'حاضر';
            let statusClass = 'status-present';
            
            // Check if any subject shows absent
            const subjects = Object.keys(dayData);
            const absentCount = subjects.filter(s => dayData[s] === 'غائب').length;
            const totalSubjects = subjects.length;
            
            if (absentCount === totalSubjects) {
                statusText = 'غائب';
                statusClass = 'status-absent';
            } else if (absentCount > 0) {
                statusText = `حضور جزئي (${totalSubjects - absentCount}/${totalSubjects})`;
                statusClass = 'status-partial';
            }
            
            return `
                <tr>
                    <td>${formatDate(date)}</td>
                    <td><span class="${statusClass}">${statusText}</span></td>
                    <td>${subjects.length > 0 ? subjects.join(', ') : '-'}</td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = rows || '<tr><td colspan="3">لا يوجد سجل حضور</td></tr>';
    } else {
        // Use simple attendance
        const sortedDates = Object.keys(attendance).sort().reverse();
        
        const rows = sortedDates.map(date => `
            <tr>
                <td>${formatDate(date)}</td>
                <td><span class="status-${attendance[date] ? 'present' : 'absent'}">
                    ${attendance[date] ? 'حاضر' : 'غائب'}
                </span></td>
                <td>-</td>
            </tr>
        `).join('');

        tbody.innerHTML = rows || '<tr><td colspan="3">لا يوجد سجل حضور</td></tr>';
    }
}

// تسجيل الخروج
function logout() {
    localStorage.removeItem('student');
    window.location.reload();
}

// مساعدة في معالجة JSON
function parseJSON(str) {
    try {
        if (typeof str === 'object' && str !== null) return str;
        return JSON.parse(str || '{}');
    } catch {
        return {};
    }
}

// تنسيق التاريخ
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ar-SA');
}

// الحصول على التقدير (legacy support)
function getGradeText(score) {
    const thresholds = currentStudent ? getThresholdsForStudent(currentStudent) : GRADE_THRESHOLDS.scale100;
    const status = getGradeStatus(score, thresholds);
    return status.text;
}

// الحصول على فئة التقدير (legacy support)
function getGradeClass(score) {
    const thresholds = currentStudent ? getThresholdsForStudent(currentStudent) : GRADE_THRESHOLDS.scale100;
    const status = getGradeStatus(score, thresholds);
    return status.cssClass.replace('grade-', '');
}

// ============================================================================
// ACADEMIC YEAR MANAGEMENT FOR STUDENT PORTAL
// ============================================================================

// Load academic years for the student's school
// The current year is automatically determined by the server based on the present date
async function loadAcademicYears() {
    if (!currentStudent || !currentStudent.school_id) {
        console.log('No student or school_id available');
        return;
    }

    try {
        const response = await fetch(`/api/school/${currentStudent.school_id}/academic-years`);
        const result = await response.json();

        if (result.success && result.academic_years && result.academic_years.length > 0) {
            academicYears = result.academic_years;
            
            // Find current academic year (automatically determined by server based on date)
            const currentYear = academicYears.find(y => y.is_current === 1) || academicYears[0];
            
            if (currentYear) {
                currentAcademicYearId = currentYear.id;
            }

            updateAcademicYearSelector();
            
            // Show the selector if it exists
            const selectorContainer = document.getElementById('academicYearSelectorContainer');
            if (selectorContainer) {
                selectorContainer.style.display = 'flex';
            }
        }
    } catch (error) {
        console.error('Error loading academic years:', error);
    }
}

// Update academic year selector dropdown
// The current year is marked automatically based on the present date
function updateAcademicYearSelector() {
    const select = document.getElementById('academicYearSelect');
    if (!select) return;
    
    select.innerHTML = '';

    academicYears.forEach(year => {
        const isCurrent = year.is_current === 1;
        const option = document.createElement('option');
        option.value = year.id;
        option.textContent = isCurrent ? `${year.name} (الحالية)` : year.name;
        if (isCurrent || currentAcademicYearId === year.id) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    // If we have a current year, select it
    if (currentAcademicYearId) {
        select.value = currentAcademicYearId;
        selectedAcademicYearId = currentAcademicYearId;
    }

    updateAcademicYearBadge();
}

// Update academic year badge display
function updateAcademicYearBadge() {
    const badge = document.getElementById('academicYearBadge');
    const badgeText = document.getElementById('academicYearBadgeText');
    
    if (!badge || !badgeText) return;

    if (selectedAcademicYearId === 'current' || !selectedAcademicYearId) {
        badge.style.display = 'none';
    } else {
        const selectedYear = academicYears.find(y => y.id == selectedAcademicYearId);
        if (selectedYear) {
            badgeText.textContent = selectedYear.name;
            badge.style.display = 'inline-block';
        }
    }
}

// Handle academic year change
async function onAcademicYearChange() {
    const select = document.getElementById('academicYearSelect');
    if (!select) return;
    
    selectedAcademicYearId = select.value;

    updateAcademicYearBadge();

    // If "current" is selected or we have the current year selected, load default data
    if (selectedAcademicYearId === 'current' || selectedAcademicYearId == currentAcademicYearId) {
        displayStudentData();
    } else {
        // Load data for the selected academic year
        await loadDataForAcademicYear(selectedAcademicYearId);
    }
}

// Load grades and attendance for a specific academic year
async function loadDataForAcademicYear(yearId) {
    if (!currentStudent) return;

    try {
        // Load grades for the year
        const gradesResponse = await fetch(`/api/student/${currentStudent.id}/grades/${yearId}`);
        const gradesResult = await gradesResponse.json();

        // Load attendance for the year
        const attendanceResponse = await fetch(`/api/student/${currentStudent.id}/attendance/${yearId}`);
        const attendanceResult = await attendanceResponse.json();

        // Display data
        if (gradesResult.success && gradesResult.grades) {
            displayScoresForYear(gradesResult.grades);
        } else {
            const tbody = document.getElementById('scoresTableBody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="4">لا توجد درجات مسجلة لهذه السنة الدراسية</td></tr>';
            }
        }

        if (attendanceResult.success && attendanceResult.attendance && attendanceResult.attendance.length > 0) {
            displayAttendanceForYear(attendanceResult.attendance);
        } else {
            const tbody = document.getElementById('attendanceTableBody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="3">لا توجد سجلات حضور لهذه السنة الدراسية</td></tr>';
            }
        }

        // Update recommendations for this year's data
        if (gradesResult.success && gradesResult.grades) {
            updateRecommendationsForYear(gradesResult.grades);
        }

    } catch (error) {
        console.error('Error loading data for academic year:', error);
    }
}

// Display grades for a specific academic year
function displayScoresForYear(grades) {
    const tbody = document.getElementById('scoresTableBody');
    if (!tbody) return;

    const thresholds = getThresholdsForStudent(currentStudent);
    const maxGrade = thresholds.maxGrade;

    if (grades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4">لا توجد درجات مسجلة لهذه السنة</td></tr>';
        return;
    }

    const rows = grades.map(grade => {
        const scores = {
            month1: grade.month1 || 0,
            month2: grade.month2 || 0,
            midterm: grade.midterm || 0,
            month3: grade.month3 || 0,
            month4: grade.month4 || 0,
            final: grade.final || 0
        };

        // Calculate average
        let total = 0;
        let count = 0;
        for (const period in scores) {
            if (scores[period] > 0) {
                total += scores[period];
                count++;
            }
        }
        const avg = count > 0 ? total / count : 0;
        const status = getGradeStatus(avg, thresholds);

        return `
            <tr>
                <td>${grade.subject_name}</td>
                <td>${avg.toFixed(1)}/${maxGrade}</td>
                <td><span class="${status.cssClass}">${status.text}</span></td>
                <td>${status.recommendation}</td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = rows;
}

// Display attendance for a specific academic year
function displayAttendanceForYear(attendanceRecords) {
    const tbody = document.getElementById('attendanceTableBody');
    if (!tbody) return;

    if (attendanceRecords.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3">لا توجد سجلات حضور لهذه السنة</td></tr>';
        return;
    }

    // Sort by date descending
    attendanceRecords.sort((a, b) => new Date(b.attendance_date) - new Date(a.attendance_date));

    const rows = attendanceRecords.map(record => {
        let statusText = 'حاضر';
        let statusClass = 'status-present';

        if (record.status === 'absent') {
            statusText = 'غائب';
            statusClass = 'status-absent';
        } else if (record.status === 'late') {
            statusText = 'متأخر';
            statusClass = 'status-late';
        } else if (record.status === 'excused') {
            statusText = 'معذور';
            statusClass = 'status-excused';
        }

        return `
            <tr>
                <td>${formatDate(record.attendance_date)}</td>
                <td><span class="${statusClass}">${statusText}</span></td>
                <td>${record.notes || '-'}</td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = rows;
}

// Update recommendations for a specific academic year
function updateRecommendationsForYear(grades) {
    // Convert grades array to detailed_scores format
    const detailedScores = {};
    grades.forEach(grade => {
        detailedScores[grade.subject_name] = {
            month1: grade.month1 || 0,
            month2: grade.month2 || 0,
            midterm: grade.midterm || 0,
            month3: grade.month3 || 0,
            month4: grade.month4 || 0,
            final: grade.final || 0
        };
    });

    const recommendationsContainer = document.getElementById('recommendationsContainer');
    if (!recommendationsContainer) return;

    if (Object.keys(detailedScores).length === 0) {
        recommendationsContainer.innerHTML = '<div class="recommendations-section"><p>لا توجد درجات مسجلة لهذه السنة</p></div>';
        return;
    }

    const thresholds = getThresholdsForStudent(currentStudent);
    const maxGrade = thresholds.maxGrade;

    const advisor = new StudentAcademicAdvisor(detailedScores, maxGrade, thresholds);
    recommendationsContainer.innerHTML = advisor.generateFullHTML();
}