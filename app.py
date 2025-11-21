from flask import Flask, render_template, request
import requests

app = Flask(__name__)

APP_ID = "fda6ebd6"
APP_KEY = "c5ea8ba289281cbbbdb154d3178f6db9"

ACTIVITY_MULTIPLIERS = {
    "sedentario": 1.2,
    "ligero": 1.375,
    "moderado": 1.55,
    "activo": 1.725,
    "muy_activo": 1.9
}

def calculate_bmi(weight, height):
    """Calcula el Índice de Masa Corporal (kg/m^2)."""
    if height == 0: return None
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

def interpret_bmi(bmi):
    """Devuelve la interpretación del IMC."""
    if bmi is None: return "Datos inválidos"
    if bmi < 18.5: return "Bajo peso"
    elif bmi < 24.9: return "Peso normal"
    elif bmi < 29.9: return "Sobrepeso"
    else: return "Obesidad"

def calculate_bmr(weight, height, age, gender):
    """Calcula la Tasa Metabólica Basal (TMB) usando Mifflin-St Jeor."""
    if gender == 'male':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif gender == 'female':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    else:
        return None
    return round(bmr, 0)

def calculate_tdee(bmr, activity_level):
    """Calcula el Gasto Calórico Total (GCT) o TDEE."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    if bmr is None: return None
    tdee = bmr * multiplier
    return round(tdee, 0)

def calculate_ideal_weight(height, gender):
    """Calcula el Peso Corporal Ideal (PCI) usando una fórmula simple (Devine/Hamwi adaptada a métrico)."""
    if height < 152.4:
        if gender == 'male':
            return 50
        elif gender == 'female':
            return 45.5
        else:
            return None

    if gender == 'male':
        pci = 50 + 0.91 * (height - 152.4)
    elif gender == 'female':
        pci = 45.5 + 0.91 * (height - 152.4)
    else:
        return None
    
    return round(pci, 1)

def calculate_macros(tdee, carb_perc, prot_perc, fat_perc):
    """Calcula las macros en gramos basado en el GCT y porcentajes."""
    if tdee is None or (carb_perc + prot_perc + fat_perc) != 100:
        return None

    carb_kcal = tdee * (carb_perc / 100)
    prot_kcal = tdee * (prot_perc / 100)
    fat_kcal = tdee * (fat_perc / 100)
    
    carb_g = round(carb_kcal / 4, 1)
    prot_g = round(prot_kcal / 4, 1)
    fat_g = round(fat_kcal / 9, 1)
    
    return {
        "carbohidratos_g": carb_g,
        "proteinas_g": prot_g,
        "grasas_g": fat_g,
        "total_kcal_verificacion": carb_kcal + prot_kcal + fat_kcal
    }


@app.route("/")
def index():
    """Ruta principal."""
    return render_template("index.html")

@app.route("/calculadoras")
def calculadoras():
    """Ruta para la página principal de calculadoras."""
    return render_template("calculadoras.html")

@app.route("/calcular", methods=["POST"])
def calcular():
    """Maneja las peticiones de cálculo de todas las calculadoras."""
    calculator_type = request.form.get("calculator_type")
    
    results = {}
    
    try:
        if calculator_type == "imc":
            weight = float(request.form.get("weight_imc"))
            height = float(request.form.get("height_imc"))
            
            bmi = calculate_bmi(weight, height)
            interpretation = interpret_bmi(bmi)
            
            results = {
                "tipo": "imc",
                "imc": bmi,
                "interpretacion": interpretation,
                "titulo": "Resultado de Índice de Masa Corporal (IMC)"
            }
            
        elif calculator_type == "tmb_gct":
            weight = float(request.form.get("weight_tmb"))
            height = float(request.form.get("height_tmb"))
            age = int(request.form.get("age_tmb"))
            gender = request.form.get("gender_tmb")
            activity_level = request.form.get("activity_level_tmb")

            bmr = calculate_bmr(weight, height, age, gender)
            tdee = calculate_tdee(bmr, activity_level)
            ideal_weight = calculate_ideal_weight(height, gender)
            
            results = {
                "tipo": "tmb_gct",
                "tmb": bmr,
                "gct": tdee,
                "peso_ideal": ideal_weight,
                "titulo": "Tasa Metabólica, Gasto Calórico y Peso Ideal"
            }
            
        elif calculator_type == "macros":
            tdee = float(request.form.get("tdee_macros"))
            carb_perc = float(request.form.get("carb_perc"))
            prot_perc = float(request.form.get("prot_perc"))
            fat_perc = float(request.form.get("fat_perc"))
            
            macros = calculate_macros(tdee, carb_perc, prot_perc, fat_perc)
            
            results = {
                "tipo": "macros",
                "macros": macros,
                "titulo": "Distribución Recomendada de Macronutrientes"
            }

        elif calculator_type == "recetas":
            ingrediente = request.form.get("ingrediente")
            
            if not ingrediente:
                results = {"tipo": "error", "mensaje": "Debes escribir un ingrediente para la búsqueda."}
                return render_template("calculadoras.html", results=results)

            url = "https://api.edamam.com/search"
            params = {
                "q": ingrediente,
                "app_id": APP_ID,
                "app_key": APP_KEY,
                "to": 9
            }
            response = requests.get(url, params=params)

            recetas = []
            if response.status_code == 200:
                try:
                    data = response.json()
                    recetas = data.get("hits", [])
                except ValueError:
                    print("La respuesta no es JSON válido:", response.text[:200])
                    results = {"tipo": "error", "mensaje": "Error al procesar la respuesta de la API de recetas."}
            else:
                print("Error en la API:", response.status_code, response.text[:200])
                results = {"tipo": "error", "mensaje": f"Error de conexión con la API: {response.status_code}"}
            
            results = {
                "tipo": "recetas",
                "ingrediente": ingrediente,
                "recetas": recetas,
                "titulo": f"Recetas encontradas para: {ingrediente}"
            }
            
        else:
            results = {"tipo": "error", "mensaje": "Tipo de calculadora no reconocido."}
            
    except ValueError:
        results = {"tipo": "error", "mensaje": "Asegúrate de ingresar valores numéricos válidos en todos los campos."}
    except Exception as e:
        results = {"tipo": "error", "mensaje": f"Ocurrió un error inesperado: {str(e)}"}


    return render_template("calculadoras.html", results=results)


if __name__ == "__main__":
    app.run(debug=True)