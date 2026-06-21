def importe_total_carrito(request):
    total = 0
    if request.user.is_authenticated or not request.user.is_authenticated: # Para todos
        if "cart" in request.session:
            for key, value in request.session["cart"].items():
                total += float(value["acumulado"])
    return {"importe_total_carrito": total}